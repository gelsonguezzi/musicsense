"""MusicSense 218: authorized original-video download and six-stem separation."""
from pathlib import Path
import subprocess,tempfile,uuid,shutil
from youtube_support import video_id_from_url,YTDLP,FFMPEG,fetch_audio_for_playback

def download_original(url,cache,progress=None):
    vid=video_id_from_url(url)
    if not YTDLP.is_file():raise RuntimeError('yt-dlp indisponivel')
    if progress:progress(8,'Obtendo a melhor qualidade disponivel')
    with tempfile.TemporaryDirectory(prefix='ms_original_') as tmp:
        target=Path(tmp)/'original.%(ext)s'
        cmd=[str(YTDLP),'--ignore-config','--no-playlist','--no-warnings',
             '--ffmpeg-location',str(FFMPEG),'-f','bv*+ba/b',
             '--merge-output-format','mp4','--remux-video','mp4',
             '-o',str(target),'https://www.youtube.com/watch?v='+vid]
        cookies=Path(r'C:\Yt-dlp\www.youtube.com_cookies.txt')
        if cookies.is_file() and cookies.stat().st_size>100:cmd[1:1]=['--cookies',str(cookies)]
        try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=1200)
        except subprocess.TimeoutExpired:raise RuntimeError('Tempo limite excedido ao baixar video')
        if r.returncode:raise RuntimeError('Download indisponivel: '+(r.stderr or r.stdout)[-500:])
        files=[x for x in Path(tmp).glob('original.*') if x.is_file()]
        if not files:raise RuntimeError('Nenhum video foi produzido')
        source=max(files,key=lambda f:f.stat().st_size)
        if progress:progress(95,'Preparando arquivo MP4')
        output=cache/('musicsense_original_'+vid+'_'+uuid.uuid4().hex[:8]+'.mp4')
        shutil.move(str(source),str(output))
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
