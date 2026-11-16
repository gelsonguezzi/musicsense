"""Exportacao de video original, para conteudo autorizado."""
import json,subprocess,tempfile,uuid,shutil,urllib.request,re
from pathlib import Path
from youtube_support import video_id_from_url,YTDLP,FFMPEG
from studio_export import make_ass
def export_youtube_video(url,segments,cache,title="",language="en"):
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
        ass=temp/'captions.ass'
        subtitles=make_ass(segments).replace('PlayResX: 720','PlayResX: 1280').replace('PlayResY: 900','PlayResY: 720').replace('Arial,32,','Arial,50,').replace('Arial,26,','Arial,43,').replace('50,50,135,','105,105,108,').replace('50,50,70,','105,105,42,')
        # Smaller type for unusually long lines, preserving the 20% increase for normal phrases.
        lines=[]
        for line in subtitles.splitlines():
            if line.startswith('Dialogue: '):
                parts=line.split(',',9)
                if len(parts)==10:
                    length=len(parts[9])
                    if length>66:parts[9]=r'{\fs34}'+parts[9]
                    elif length>48:parts[9]=r'{\fs40}'+parts[9]
                    line=','.join(parts)
            lines.append(line)
        ass.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
        output=cache/('musicsense_video_'+uuid.uuid4().hex[:12]+'.mp4')
        ffmpeg=Path(FFMPEG)/'ffmpeg.exe'
        # Create a two-second cinematic cover using the YouTube image (or a frame from the video).
        cover=temp/'cover.jpg'
        for quality in ('maxresdefault','sddefault','hqdefault'):
            try:
                request=urllib.request.Request('https://i.ytimg.com/vi/'+vid+'/'+quality+'.jpg',headers={'User-Agent':'Mozilla/5.0'})
                with urllib.request.urlopen(request,timeout=9) as response:
                    blob=response.read(6*1024*1024)
                if len(blob)>12000:
                    cover.write_bytes(blob);break
            except Exception:pass
        if not cover.exists():
            probe=subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-y','-ss','1','-i',str(source),'-frames:v','1',str(cover)],capture_output=True,timeout=35)
            if probe.returncode or not cover.exists():raise RuntimeError('Nao foi possivel criar a capa do videoclipe')
        # Do not invent a translated title when no local translation is available.
        full_title=str(title or '').strip()
        if not full_title or full_title.startswith('YouTube '):
            try:
                info=subprocess.run([str(YTDLP),'--ignore-config','--no-warnings','--skip-download','--print','%(title)s','https://www.youtube.com/watch?v='+vid],capture_output=True,text=True,timeout=30)
                full_title=info.stdout.strip().splitlines()[-1] if info.returncode==0 and info.stdout.strip() else ''
            except Exception:pass
        full_title=re.sub(r'(?i)\s*[\[(](official|music video|lyrics?|hd|4k)[^\])]*[\])]','',full_title).strip() or 'Videoclipe'
        parts=re.split(r'\s+[-–—]\s+',full_title,maxsplit=1)
        artist=parts[0] if len(parts)>1 else 'MusicSense AI'
        song=parts[1] if len(parts)>1 else full_title
        translated=''
        try:
            from server import translate_lines
            translated=translate_lines([song],str(language or 'en').lower().split('-')[0])[0][0].strip()
        except Exception:pass
        if translated.casefold()==song.casefold():translated=''
        def cover_text(name,value):
            path=temp/name
            path.write_text(value[:160],encoding='utf-8')
            return name
        artist_file=cover_text('artist.txt',artist)
        song_file=cover_text('song.txt',song)
        translation_file=cover_text('translated.txt',translated)
        font=r'C\:/Windows/Fonts/arialbd.ttf'
        # Text is read from UTF-8 files to avoid FFmpeg escaping failures with artist names.
        cover_filter=(
            '[1:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,'
            'eq=brightness=-0.17:saturation=0.9,'
            'drawbox=x=0:y=430:w=iw:h=290:color=black@0.62:t=fill,'
            "drawtext=fontfile='"+font+"':textfile='"+artist_file+"':fontcolor=0xffdf90:fontsize=39:x=(w-text_w)/2:y=470,"
            "drawtext=fontfile='"+font+"':textfile='"+song_file+"':fontcolor=white:fontsize=55:x=(w-text_w)/2:y=530,"
            "drawtext=fontfile='"+font+"':textfile='"+translation_file+"':fontcolor=0xffd277:fontsize=34:x=(w-text_w)/2:y=614[cover];"
            '[0:v]scale=1280:720:force_original_aspect_ratio=decrease,'
            'pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,subtitles='+ass.name+'[main];'
            '[main][cover]overlay=0:0:enable=\'lt(t,2.3)\':eof_action=pass[v]'
        )
        cmd=[str(ffmpeg),'-hide_banner','-loglevel','error','-y','-i',str(source),'-loop','1','-framerate','25','-i',str(cover),
             '-t','360','-shortest','-filter_complex',cover_filter,'-map','[v]','-map','0:a:0?',
             '-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p',
             '-c:a','aac','-b:a','160k','-movflags','+faststart',str(output)]
        try: result=subprocess.run(cmd,cwd=temp,capture_output=True,text=True,timeout=600)
        except subprocess.TimeoutExpired:raise RuntimeError('Renderizacao excedeu 10 minutos')
        if result.returncode or not output.exists():
            output.unlink(missing_ok=True)
            raise RuntimeError('FFmpeg: '+result.stderr[-600:])
        return '/cache/'+output.name
