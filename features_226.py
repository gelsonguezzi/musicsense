"""MusicSense 226: multi-estagios com instrumentos realmente separados.
Mantem a linha aprovada de seis trilhas; a expansao de bateria usa modelo DrumSep.
"""
import json
import subprocess
import tempfile
import uuid
from pathlib import Path

from features_218 import separate_six
from youtube_support import video_id_from_url, FFMPEG

ROOT=Path(__file__).resolve().parent
PY=ROOT/'.venv_demucs'/'Scripts'/'python.exe'
MODEL=ROOT/'models_226'/'model_drumsep.th'
DRUM_KEYS=('kick','snare','cymbals','toms')


def valid_tracks(cache, tracks):
    return (isinstance(tracks,dict) and 1<=len(tracks)<=10 and all(
        isinstance(value,str) and value.startswith('/cache/musicsense_stem_')
        and (cache/Path(value).name).is_file()
        and (cache/Path(value).name).stat().st_size>12000
        for value in tracks.values()))


def separate_detailed(url, cache, progress=None):
    video_id=video_id_from_url(url)
    manifest=cache/('youtube_'+video_id+'_stems_228.json')
    # Mantem compatibilidade com caches detalhados da versao 226.
    # Nunca recalcula nove trilhas ja prontas apenas porque mudou a versao.
    old_manifest=cache/('youtube_'+video_id+'_stems_226.json')
    for candidate in (manifest,old_manifest):
        if candidate.is_file():
            try:
                cached=json.loads(candidate.read_text(encoding='utf-8'))
                if valid_tracks(cache,cached.get('tracks')) and cached.get('version') in (226,228):
                    if progress:progress(97,'Trilhas detalhadas recuperadas do cache')
                    return {'tracks':cached['tracks'],
                            'quality':cached.get('quality','standard'),
                            'note':cached.get('note','')}
            except (OSError,ValueError,KeyError,TypeError):pass
    if progress:progress(3,'Preparando audio de alta qualidade')
    # Nao repetir a separacao pesada em alta qualidade para obter instrumentos extras.
    # Primeiro reutiliza a separacao rapida de seis canais, que o usuario aprovou.
    base=separate_six(url,cache,
        progress=(lambda n,s:progress(min(68,max(3,int(n*.68))),s)) if progress else None,
        quality='standard')
    base_tracks=dict(base['tracks'])
    tracks=base_tracks.copy()
    note='Piano obtido do modelo experimental Demucs 6s; qualidade variavel.'
    if not MODEL.is_file() or MODEL.stat().st_size<10000000 or not PY.is_file():
        if progress:progress(95,'Modelo extra de bateria indisponivel; preservadas seis trilhas')
        return {'tracks':tracks,'quality':'standard','note':note+' Separacao detalhada indisponivel.'}
    drum_path=cache/Path(base_tracks['drums']).name
    if progress:progress(69,'IA detalhando a bateria em quatro componentes')
    with tempfile.TemporaryDirectory(prefix='ms226_drumsep_') as temp:
        folder=Path(temp)
        command=[str(PY),str(ROOT/'drumsep_226.py'),'--input',str(drum_path),
                 '--output',str(folder)]
        proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,errors='replace',bufsize=1)
        lines=[]
        try:
            for line in proc.stdout:
                line=line.strip();lines.append(line)
                if len(lines)>50:lines.pop(0)
                if line.startswith('STAGE ') and progress:
                    try:
                        step=int(line.split(' ',2)[1])
                        progress(69+(step-1)*4,line.split(' ',2)[2])
                    except (ValueError,IndexError):pass
            if proc.wait(timeout=2700):
                raise RuntimeError('DrumSep: '+' | '.join(lines[-8:]))
            files=[(key,folder/(key+'.wav')) for key in DRUM_KEYS]
            usable=[(key,path) for key,path in files if path.is_file()]
            if len(usable)<2:
                raise RuntimeError('Bateria sem componentes separaveis')
            detailed={}
            for i,(key,path) in enumerate(usable):
                output=cache/('musicsense_stem_'+key+'_'+uuid.uuid4().hex[:10]+'.mp3')
                command=[str(Path(FFMPEG)/'ffmpeg.exe'),'-hide_banner','-loglevel',
                         'error','-y','-i',str(path),'-c:a','libmp3lame',
                         '-q:a','0',str(output)]
                result=subprocess.run(command,capture_output=True,text=True,timeout=180)
                if result.returncode or not output.is_file():
                    output.unlink(missing_ok=True)
                    raise RuntimeError('Falha ao converter '+key+': '+result.stderr[-250:])
                detailed[key]='/cache/'+output.name
                if progress:progress(84+int((i+1)*12/max(1,len(usable))),
                                      'Preparando bateria: '+key)
            # Nao tocar bateria inteira e pecas simultaneamente (duplicaria audio).
            tracks.pop('drums',None)
            tracks.update(detailed)
            note='Bateria separada por DrumSep: componentes estimados por IA. '+note
        except Exception as exc:
            # O trabalho aprovado nao deve se perder se o modelo complementar falhar.
            note='Separacao detalhada indisponivel ('+str(exc)[:120]+'). '+note
            tracks=base_tracks
        finally:
            if proc.poll() is None:proc.kill()
    tracks={key:tracks[key] for key in (
        'vocals','lead_vocals','backing_vocals','drums',
        'kick','snare','cymbals','toms','bass','guitar','piano','other'
    ) if key in tracks}
    if len(tracks)>10:
        tracks=dict(list(tracks.items())[:10])
    data={'version':228,'tracks':tracks,'quality':'standard','note':note}
    manifest.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    if progress:progress(99,str(len(tracks))+' trilhas para a mesa')
    return {'tracks':tracks,'quality':'standard','note':note}
