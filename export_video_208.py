"""Exportacao de video original, para conteudo autorizado."""
import json,subprocess,tempfile,uuid,shutil
from pathlib import Path
from youtube_support import video_id_from_url,YTDLP,FFMPEG
from studio_export import make_ass
def export_youtube_video(url,segments,cache):
    vid=video_id_from_url(url)
    if not isinstance(segments,list) or not 1<=len(segments)<=500:raise ValueError('Legendas invalidas')
    if not YTDLP.is_file():raise RuntimeError('yt-dlp nao encontrado')
    with tempfile.TemporaryDirectory(prefix='musicsense_clip_') as tmp:
        temp=Path(tmp)
        canonical='https://www.youtube.com/watch?v='+vid
        cmd=[str(YTDLP),'--ignore-config','--no-playlist','--no-warnings',
            '--max-filesize','100M','--ffmpeg-location',str(FFMPEG),
            '-f','bv*[height<=720]+ba/b[height<=720]/best',
            '--merge-output-format','mp4','--remux-video','mp4',
            '-o',str(temp/'clip.%(ext)s'),canonical]
        cookies=Path(r'C:\Yt-dlp\www.youtube.com_cookies.txt')
        if cookies.is_file() and cookies.stat().st_size>100:
            cmd[1:1]=['--cookies',str(cookies)]
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        if proc.returncode:
            raise RuntimeError('Nao foi possivel obter o video: '+(proc.stderr or proc.stdout)[-500:])
        files=list(temp.glob('clip.*'))
        if not files:raise RuntimeError('Video nao encontrado apos download')
        source=max(files,key=lambda f:f.stat().st_size)
        if source.stat().st_size>100*1024*1024:raise ValueError('Video excede 100 MB')
        ass=temp/'captions.ass';ass.write_text(make_ass(segments).replace('PlayResX: 720','PlayResX: 1280').replace('PlayResY: 900','PlayResY: 720').replace('Arial,32,','Arial,42,').replace('Arial,26,','Arial,36,').replace('50,50,135,','50,50,105,').replace('50,50,70,','50,50,40,'),encoding='utf-8-sig')
        output=cache/('musicsense_video_'+uuid.uuid4().hex[:12]+'.mp4')
        ffmpeg=Path(FFMPEG)/'ffmpeg.exe'
        cmd=[str(ffmpeg),'-hide_banner','-loglevel','error','-y','-i',str(source),
            '-t','360','-vf','scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,subtitles='+str(ass.name),
            '-map','0:v:0','-map','0:a:0?','-c:v','libx264','-preset','veryfast','-crf','24',
            '-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(output)]
        try: result=subprocess.run(cmd,cwd=temp,capture_output=True,text=True,timeout=600)
        except subprocess.TimeoutExpired:raise RuntimeError('Renderizacao excedeu 10 minutos')
        if result.returncode or not output.exists():
            output.unlink(missing_ok=True)
            raise RuntimeError('FFmpeg: '+result.stderr[-600:])
        return '/cache/'+output.name
