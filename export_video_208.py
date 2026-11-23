"""Exportacao do videoclipe original com capa e legendas, MusicSense 222."""
import subprocess
import tempfile
from pathlib import Path

from youtube_support import video_id_from_url, YTDLP, FFMPEG
from cover_card_222 import render_captioned_video


def export_youtube_video(url, segments, cache, title="", language="en", progress=None):
    video_id = video_id_from_url(url)
    if not isinstance(segments, list) or not 1 <= len(segments) <= 500:
        raise ValueError("Legendas invalidas")
    if not YTDLP.is_file():
        raise RuntimeError("yt-dlp nao encontrado")
    with tempfile.TemporaryDirectory(prefix="musicsense_clip_") as temp_name:
        temp = Path(temp_name)
        canonical = "https://www.youtube.com/watch?v=" + video_id
        # Reutiliza videoclipe ja baixado pela ferramenta "Salvar clipe original".
        # Isso evita baixar o mesmo arquivo toda vez que o usuario adiciona legendas.
        existing=sorted((p for p in cache.glob("musicsense_original_"+video_id+"_*.mp4")
                         if 10000<p.stat().st_size<=100*1024*1024),key=lambda p:p.stat().st_size)
        source=existing[0] if existing else None
        if source is not None:
            if progress:progress(40,'Videoclipe original encontrado no cache; sem novo download')
        else:
            if progress:progress(5,'Conectando ao YouTube e iniciando download')
        cmd = [str(YTDLP), "--ignore-config", "--no-playlist", "--no-warnings",
               "--newline", "--progress", "--progress-template",
               "download:MSPROGRESS %(progress._percent_str)s",
               "--max-filesize", "100M", "--ffmpeg-location", str(FFMPEG),
               "-f", "bv*[height<=720]+ba/b[height<=720]/best",
               "--merge-output-format", "mp4", "--remux-video", "mp4",
               "-o", str(temp / "clip.%(ext)s"), canonical]
        cookies = Path(r"C:\Yt-dlp\www.youtube.com_cookies.txt")
        if cookies.is_file() and cookies.stat().st_size > 100:
            cmd[1:1] = ["--cookies", str(cookies)]
        import re, time
        if source is None:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, errors="replace", bufsize=1)
            lines=[];start=time.monotonic();percent=5
            try:
                for line in proc.stdout:
                    lines.append(line.strip())
                    if len(lines)>50:lines.pop(0)
                    match=re.search(r"MSPROGRESS\s+([\d.,]+)%",line)
                    if match and progress:
                        value=float(match.group(1).replace(",","."))
                        percent=max(percent,5+int(value*.35))
                        progress(percent,"Baixando videoclipe: "+str(round(value))+"% do arquivo")
                    if time.monotonic()-start>300:
                        proc.kill();raise RuntimeError("Download excedeu cinco minutos")
                if proc.wait(timeout=20):
                    raise RuntimeError("Nao foi possivel obter o video: "+" ".join(lines)[-500:])
            finally:
                if proc.poll() is None:proc.kill()
            files = [f for f in temp.glob("clip.*") if f.suffix.lower() in (".mp4", ".webm", ".mkv")]
            if not files:
                raise RuntimeError("Video nao encontrado apos download.")
            source = max(files, key=lambda f: f.stat().st_size)
            if source.stat().st_size > 100 * 1024 * 1024:
                raise ValueError("Video excede 100 MB")
        if progress:progress(42,'Videoclipe recebido; preparando capa e legendas')
        return render_captioned_video(source, cache, temp, video_id, segments,
                                      title, language, progress=progress)
