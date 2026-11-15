"""MusicSense 218: authorized original-video download and six-stem separation."""
from pathlib import Path
import subprocess,tempfile,uuid,shutil,re
from youtube_support import video_id_from_url,YTDLP,FFMPEG,fetch_audio_for_playback

def download_original(url,cache,progress=None):
    import threading
    vid=video_id_from_url(url)
    if not YTDLP.is_file():raise RuntimeError('yt-dlp indisponivel')
    if progress:progress(5,'Conectando ao YouTube')
    with tempfile.TemporaryDirectory(prefix='ms_original_') as tmp:
        target=Path(tmp)/'original.%(ext)s'
        cmd=[str(YTDLP),'--ignore-config','--no-playlist','--no-warnings',
             '--newline','--progress','--progress-template',
             'download:MSPROGRESS %(progress._percent_str)s %(progress._speed_str)s %(progress._eta_str)s',
             '--ffmpeg-location',str(FFMPEG),
             '-f','bv*[vcodec^=avc1]+ba[acodec^=mp4a]/bv*[vcodec^=avc1]+ba/bv*+ba/b',
             '--merge-output-format','mp4','--remux-video','mp4',
             '-o',str(target),'https://www.youtube.com/watch?v='+vid]
        cookies=Path(r'C:\Yt-dlp\www.youtube.com_cookies.txt')
        if cookies.is_file() and cookies.stat().st_size>100:cmd[1:1]=['--cookies',str(cookies)]
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',bufsize=1)
        logs=[]
        try:
            import time
            start=time.monotonic()
            for line in proc.stdout:
                logs.append(line.strip())
                if len(logs)>35:logs.pop(0)
                m=re.search(r'MSPROGRESS\s+([\d.,]+)%',line)
                if m and progress:
                    pct=float(m.group(1).replace(',','.'))
                    progress(7+int(pct*.65),'Baixando video: '+str(round(pct))+'%')
                elif '[Merger]' in line or '[VideoRemuxer]' in line:
                    if progress:progress(74,'Unindo video e audio')
                if time.monotonic()-start>1200:
                    proc.kill();raise RuntimeError('Tempo limite excedido ao baixar video')
            if proc.wait(timeout=30):raise RuntimeError('Download indisponivel: '+' '.join(logs)[-600:])
        finally:
            if proc.poll() is None:proc.kill()
        files=[x for x in Path(tmp).glob('original.*') if x.is_file() and x.suffix.lower() in ('.mp4','.mkv','.webm')]
        if not files:raise RuntimeError('Nenhum video foi produzido')
        source=max(files,key=lambda f:f.stat().st_size)
        probe=Path(FFMPEG)/'ffprobe.exe'
        meta=subprocess.run([str(probe),'-v','error','-show_entries','stream=codec_name,codec_type','-of','json',str(source)],capture_output=True,text=True,timeout=30)
        if meta.returncode:raise RuntimeError('Arquivo de video invalido: '+meta.stderr[-250:])
        import json
        streams=json.loads(meta.stdout).get('streams',[])
        vc=next((x.get('codec_name') for x in streams if x.get('codec_type')=='video'),None)
        ac=next((x.get('codec_name') for x in streams if x.get('codec_type')=='audio'),None)
        if not vc:raise RuntimeError('Arquivo sem faixa de video')
        output=cache/('musicsense_original_'+vid+'_'+uuid.uuid4().hex[:8]+'.mp4')
        if vc=='h264' and ac=='aac' and source.suffix.lower()=='.mp4':
            if progress:progress(96,'Validando MP4 compativel')
            shutil.move(str(source),str(output))
        else:
            if progress:progress(77,'Convertendo para MP4 compativel (H.264 + AAC)')
            ff=Path(FFMPEG)/'ffmpeg.exe'
            command=[str(ff),'-hide_banner','-loglevel','error','-y','-i',str(source),
                     '-map','0:v:0','-map','0:a:0?','-c:v','libx264','-preset','veryfast','-crf','19',
                     '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',
                     '-progress','pipe:1','-nostats',str(output)]
            probe_duration=subprocess.run([str(probe),'-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(source)],capture_output=True,text=True)
            try:duration=float(probe_duration.stdout.strip())
            except:duration=0
            pr=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                for line in pr.stdout:
                    if line.startswith('out_time_ms=') and duration>0 and progress:
                        try:
                            seconds=int(line.split('=',1)[1])/1000000
                            progress(min(97,77+int(20*seconds/duration)),'Convertendo MP4: '+str(round(min(100,100*seconds/duration)))+'%')
                        except:pass
                if pr.wait(timeout=120):raise RuntimeError('Falha na conversao: '+pr.stderr.read()[-400:])
            finally:
                if pr.poll() is None:pr.kill()
        if not output.is_file() or output.stat().st_size<10000:raise RuntimeError('MP4 final nao foi gerado')
        if progress:progress(99,'MP4 compativel pronto para salvar')
        return '/cache/'+output.name

def separate_six(url,cache,progress=None):
    py=Path(__file__).parent/'.venv_demucs'/'Scripts'/'python.exe'
    if not py.is_file():raise RuntimeError('Demucs nao instalado')
    if progress:progress(5,'Obtendo audio')
    audio=fetch_audio_for_playback(url,cache)
    with tempfile.TemporaryDirectory(prefix='ms_6stems_') as tmp:
        if progress:progress(15,'Separando seis trilhas com IA. Pode levar varios minutos')
        cmd=[str(py),str(Path(__file__).parent/'demucs_compat_214.py'),'-n','htdemucs_6s','-o',tmp,str(audio)]
        try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=3600)
        except subprocess.TimeoutExpired:raise RuntimeError('Separacao excedeu 60 minutos')
        if r.returncode:raise RuntimeError('Demucs 6 trilhas: '+(r.stderr or r.stdout)[-700:])
        base=Path(tmp)/'htdemucs_6s'/audio.stem
        tracks={}
        names=['vocals','drums','bass','guitar','piano','other']
        for i,name in enumerate(names):
            src=base/(name+'.wav')
            if not src.is_file():raise RuntimeError('Trilha ausente: '+name)
            out=cache/('musicsense_stem_'+name+'_'+uuid.uuid4().hex[:10]+'.mp3')
            conv=subprocess.run([str(Path(FFMPEG)/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-y','-i',str(src),'-codec:a','libmp3lame','-q:a','3',str(out)],capture_output=True,text=True,timeout=300)
            if conv.returncode:raise RuntimeError('Falha ao gerar '+name+': '+conv.stderr[-200:])
            tracks[name]='/cache/'+out.name
            if progress:progress(65+int((i+1)*30/6),'Preparando trilha '+name)
        return {'tracks':tracks}
