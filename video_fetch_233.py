"""MusicSense 233 - reliable and legible acquisition of authorized public YouTube clips.
Respects YouTube availability; never attempts to defeat access restrictions.
"""
import json
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from youtube_support import media_from_url, YTDLP, FFMPEG

FF=Path(FFMPEG)/"ffmpeg.exe"
FP=Path(FFMPEG)/"ffprobe.exe"
MAX_BYTES=150*1024*1024
FORMATS=(
    ("Video ate 720p com audio", "bv*[height<=720]+ba/b[height<=720]"),
    ("MP4 integrado compativel", "b[ext=mp4][height<=720]/18"),
    ("Video alternativo ate 480p", "bv*[height<=480]+ba/b[height<=480]"),
)
INSTAGRAM_FORMATS=(
    ("Vídeo do Instagram", "bv*+ba/b"),
    ("MP4 integrado compatível", "b[ext=mp4]/b"),
)

def _info(path):
    r=subprocess.run([str(FP),"-v","error","-show_entries",
         "format=duration:stream=codec_type,codec_name","-of","json",str(path)],
         text=True,capture_output=True,timeout=25)
    if r.returncode:raise RuntimeError("Arquivo de video incompleto ou invalido")
    data=json.loads(r.stdout)
    videos=[x for x in data.get("streams",[]) if x.get("codec_type")=="video"]
    if not videos:raise RuntimeError("Fonte sem imagem de video")
    duration=float(data.get("format",{}).get("duration") or 0)
    if duration<1:raise RuntimeError("Video com duracao invalida")
    return duration,videos[0].get("codec_name"),any(x.get("codec_type")=="audio" for x in data.get("streams",[]))

def _cached(cache,vid):
    for p in sorted(cache.glob("musicsense_original_"+vid+"_*.mp4"),
                    key=lambda p:p.stat().st_mtime,reverse=True):
        if not p.is_file() or p.stat().st_size<15000:continue
        try:
            _info(p)
            return p
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):
            continue
    return None

def download(url,cache,progress=None):
    media=media_from_url(url)
    video_id=media["cache_id"]
    platform=media["platform"]
    platform_name="Instagram" if platform=="instagram" else "YouTube"
    cached=_cached(cache,video_id)
    if cached:
        if progress:progress(55,"Videoclipe ja salvo; reutilizando arquivo")
        return "/cache/"+cached.name
    if not YTDLP.is_file():raise RuntimeError("Ferramenta de download nao encontrada no PC")
    full_url=media["canonical"]
    formats=INSTAGRAM_FORMATS if platform=="instagram" else FORMATS
    attempts=[]
    with tempfile.TemporaryDirectory(prefix="musicsense_video233_") as folder:
        temp=Path(folder)
        for index,(label,fmt) in enumerate(formats):
            # Each fallback is an actual new format selection, never replay the
            # same rejected URL. Avoid misleading fabricated progress.
            if progress:progress(min(39,index*12+3),"Tentativa "+str(index+1)+"/3: "+label)
            prefix=temp/("candidate"+str(index))
            cmd=[str(YTDLP),"--ignore-config","--no-playlist","--no-warnings",
                 "--newline","--progress","--progress-template",
                 "download:MSPROGRESS %(progress._percent_str)s",
                 "--retries","2","--fragment-retries","2",
                 "--socket-timeout","18","--max-filesize","150M",
                 "--ffmpeg-location",str(FFMPEG),
                 "-f",fmt,"--merge-output-format","mp4",
                 "--remux-video","mp4","-o",str(prefix)+".%(ext)s",full_url]
            cookie=Path(r"C:\Yt-dlp\www."+platform+r".com_cookies.txt")
            if cookie.is_file() and cookie.stat().st_size>100:
                cmd[1:1]=["--cookies",str(cookie)]
            start=time.monotonic()
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                      text=True,errors="replace",bufsize=1)
            tail=[]
            try:
                for line in proc.stdout:
                    clean=line.strip()
                    if clean:
                        tail.append(clean)
                        if len(tail)>14:tail.pop(0)
                    match=re.search(r"MSPROGRESS\s+([\d.,]+)%",line)
                    if match and progress:
                        try:
                            number=min(100,max(0,float(match.group(1).replace(",","."))))
                            # First phase ends at 64%; monotonic even after fallback.
                            stagebase=5+index*12
                            progress(min(64,max(stagebase,stagebase+int(number*0.1))),
                              label+": "+str(round(number))+"% recebido")
                        except ValueError:pass
                    if time.monotonic()-start>240:
                        proc.kill()
                        tail.append("Tempo de obtencao excedido")
                        break
                status=proc.wait(timeout=25)
            finally:
                if proc.poll() is None:proc.kill()
            files=[x for x in temp.glob("candidate"+str(index)+".*")
                   if x.is_file() and x.suffix.lower() in (".mp4",".webm",".mkv")]
            if status==0 and files:
                source=max(files,key=lambda x:x.stat().st_size)
                try:
                    duration,codec,has_audio=_info(source)
                    if not has_audio:raise RuntimeError("Fonte nao possui audio")
                    if source.stat().st_size>MAX_BYTES:raise RuntimeError("Fonte excede 150 MB")
                    out=cache/("musicsense_original_"+video_id+"_"+uuid.uuid4().hex[:8]+".mp4")
                    if source.suffix.lower()==".mp4" and codec=="h264":
                        if progress:progress(94,"Validando MP4 e audio original")
                        shutil.move(str(source),str(out))
                    else:
                        if progress:progress(70,"Convertendo video para MP4 compativel")
                        conv=subprocess.run([str(FF),"-hide_banner","-loglevel","error","-y",
                             "-i",str(source),"-map","0:v:0","-map","0:a:0",
                             "-c:v","libx264","-preset","veryfast","-crf","21",
                             "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k",
                             "-movflags","+faststart",str(out)],
                             capture_output=True,text=True,timeout=480)
                        if conv.returncode:raise RuntimeError("Conversao MP4 indisponivel")
                    _info(out)
                    if progress:progress(99,"Videoclipe pronto para renderizacao")
                    return "/cache/"+out.name
                except (RuntimeError,ValueError,subprocess.SubprocessError) as e:
                    attempts.append(label+": "+str(e))
                    out.unlink(missing_ok=True) if "out" in locals() else None
            else:
                error=" ".join(tail)[-450:]
                if "HTTP Error 403" in error or "403: Forbidden" in error:
                    attempts.append("HTTP 403: acesso ao arquivo recusado pelo "+platform_name)
                elif "unavailable" in error.lower() or "private" in error.lower():
                    attempts.append("Vídeo não disponível no "+platform_name)
                elif "login" in error.lower() or "cookie" in error.lower():
                    attempts.append("O "+platform_name+" pediu uma sessão conectada")
                else:
                    attempts.append(label+": falha ao obter o arquivo")
            # Do not leave corrupted partial files for the next attempt.
            for f in temp.glob("candidate"+str(index)+".*"):
                f.unlink(missing_ok=True)
        detail=" ".join(attempts[-2:])
        raise RuntimeError(
          platform_name+" não permitiu baixar este videoclipe (formato indisponível ou acesso recusado). "
          +(detail+". " if detail else "")
          +"Tente novamente mais tarde; se o post for restrito, exporte a sessão do Instagram para "
           r"C:\Yt-dlp\www.instagram.com_cookies.txt."
        )
