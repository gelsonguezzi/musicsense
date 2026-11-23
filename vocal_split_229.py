"""Voz principal e backing vocals sobre o stem VOCALS ja existente (sem reexecutar Demucs)."""
import json
import re
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path

from youtube_support import video_id_from_url, FFMPEG

ROOT=Path(__file__).resolve().parent
PY=ROOT/'.venv_demucs'/'Scripts'/'python.exe'
LOCK=threading.Lock()
CATEGORIES=('vocals','drums','bass','guitar','piano','other')


def vocals_path(url, cache):
    video_id=video_id_from_url(url)
    for suffix in ('_stems6.json','_stems6_hq.json'):
        path=cache/('youtube_'+video_id+suffix)
        if not path.is_file():
            continue
        try:
            tracks=json.loads(path.read_text(encoding='utf-8')).get('tracks',{})
            stem=tracks.get('vocals','')
            if not re.fullmatch(r'/cache/musicsense_stem_vocals_[a-f0-9]{10}\.mp3',stem):
                continue
            source=cache/Path(stem).name
            if source.is_file() and source.stat().st_size>10000:
                return video_id,source
        except (OSError,KeyError,TypeError,ValueError):
            pass
    raise ValueError('Voz principal ainda nao extraida. Abra a mesa com seis trilhas primeiro.')


def valid(cache, tracks):
    return (isinstance(tracks,dict)
        and set(tracks)=={'lead_vocals','backing_vocals'}
        and all(isinstance(url,str)
          and re.fullmatch(r'/cache/musicsense_stem_(?:lead_vocals|backing_vocals)_[a-f0-9]{10}\.mp3',url)
          and (cache/Path(url).name).is_file() and (cache/Path(url).name).stat().st_size>10000
          for url in tracks.values()))


def separate(url, cache, progress=None):
    vid,source=vocals_path(url,cache)
    manifest=cache/('youtube_'+vid+'_lead_backing_229.json')
    def report(p,s):
        if progress: progress(p,s)
    def cached():
        if not manifest.is_file():
            return None
        try:
            data=json.loads(manifest.read_text(encoding='utf-8'))
            if (data.get('source')==source.name
                and data.get('source_size')==source.stat().st_size
                and valid(cache,data.get('tracks'))):
                return {'tracks':data['tracks'],
                        'note':'Voz principal e backing vocals estimados por IA; audite harmonias na musica'}
        except (OSError,TypeError,KeyError,ValueError):
            pass
        return None
    prior=cached()
    if prior:
        report(98,'Canais vocais recuperados do cache, sem reprocessar')
        return prior
    if not PY.is_file():
        raise RuntimeError('Ambiente de karaokê nao instalado')
    if not LOCK.acquire(blocking=False):
        raise RuntimeError('Ja existe uma separacao vocal em andamento; tente novamente apos concluir')
    try:
        prior=cached()
        if prior:return prior
        report(10,'Extraindo apoios vocais sem refazer os instrumentos')
        with tempfile.TemporaryDirectory(prefix='ms229_backing_') as temp:
            folder=Path(temp)
            command=[str(PY),'-u',str(ROOT/'vocal_model_229.py'),
                     '--input',str(source),'--output',str(folder)]
            report(13,'Inicializando modelo vocal na GPU')
            process=subprocess.Popen(command,stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT,text=True,errors='replace',bufsize=1)
            lines=[]
            state={'max':13,'phase':0,'last_step':0}
            def collect():
                for line in process.stdout:
                    line=line.strip()
                    if not line:continue
                    lines.append(line)
                    if len(lines)>90:lines.pop(0)
                    found=re.match(r'STAGE (\d+) (.*)',line)
                    if found:
                        percent=min(85,max(state['max'],int(found.group(1))))
                        state['max']=percent
                        report(percent,found.group(2))
                    else:
                        match=re.search(r'(\d{1,3})%\|',line)
                        if match:
                            step=min(100,int(match.group(1)))
                            if step<state['last_step']-45:
                                state['phase']=1
                            state['last_step']=step
                            pct=25+int((50 if not state['phase'] else 7)*(step/100))
                            if state['phase']:pct=75+int(7*step/100)
                            if pct>state['max']:
                                state['max']=pct
                                report(pct,'Separando voz principal e apoios vocais: '+str(step)+'% da etapa')
            reader=threading.Thread(target=collect,daemon=True)
            reader.start()
            try:
                # Limite de seguranca para evitar bloquear a maquina indefinidamente.
                returncode=process.wait(timeout=225)
                reader.join(timeout=5)
                if returncode:
                    raise RuntimeError('Separador vocal: '+' | '.join(lines[-12:])[-900:])
            except subprocess.TimeoutExpired:
                process.kill()
                reader.join(timeout=5)
                raise RuntimeError('Separacao vocal excedeu o limite de seguranca')
            files=list(folder.glob('*.wav'))
            lead=next((p for p in files if '(Vocals)' in p.name),None)
            back=next((p for p in files if '(Instrumental)' in p.name),None)
            if not lead or not back or lead==back:
                raise RuntimeError('Modelo nao devolveu voz principal e backing separados')
            tracks={}
            for number,(key,raw) in enumerate((('lead_vocals',lead),('backing_vocals',back))):
                target=cache/('musicsense_stem_'+key+'_'+uuid.uuid4().hex[:10]+'.mp3')
                cmd=[str(Path(FFMPEG)/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-y',
                     '-i',str(raw),'-c:a','libmp3lame','-q:a','2',str(target)]
                result=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
                if result.returncode or not target.is_file() or target.stat().st_size<10000:
                    target.unlink(missing_ok=True)
                    raise RuntimeError('Erro ao preparar '+key+': '+result.stderr[-350:])
                tracks[key]='/cache/'+target.name
                report(88+number*7,'Preparando '+('voz principal' if number==0 else 'backing vocals'))
            assert valid(cache,tracks)
            manifest.write_text(json.dumps({'version':229,'source':source.name,
                  'source_size':source.stat().st_size,'tracks':tracks},ensure_ascii=False),
                  encoding='utf-8')
            report(98,'Voz principal e backing prontos')
            return {'tracks':tracks,
                 'note':'Separacao vocal estimada por UVR Karaoke 2; harmonias podem conter residuos da voz principal'}
    finally:
        LOCK.release()
