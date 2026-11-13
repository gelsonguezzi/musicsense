"""Integração local de links YouTube. Não modifica C:\\Yt-dlp."""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse, parse_qs

YTDLP = Path(r"C:\Yt-dlp\yt-dlp.exe")
FFMPEG = Path(r"C:\Yt-dlp")
MAX_DURATION = 900

def video_id_from_url(url):
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"):
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    elif host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    else:
        raise ValueError("Use um link válido do YouTube.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("ID de vídeo inválido.")
    return video_id

def fetch_audio_for_playback(url, cache_dir):
    video_id = video_id_from_url(url)
    target = cache_dir / ('youtube_' + video_id + '.mp3')
    if target.is_file() and target.stat().st_size > 10000:
        return target
    if not YTDLP.is_file():
        raise RuntimeError('yt-dlp não encontrado.')
    canonical = 'https://www.youtube.com/watch?v=' + video_id
    with tempfile.TemporaryDirectory(prefix='musicsense_play_') as tmp:
        cmd = [str(YTDLP), '--ignore-config', '--no-playlist', '--no-warnings',
            '--max-filesize', '100M', '-f', 'bestaudio/best', '-x',
            '--audio-format', 'mp3', '--audio-quality', '5',
            '--ffmpeg-location', str(FFMPEG), '-o', str(Path(tmp) / 'audio.%(ext)s'), canonical]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if result.returncode:
            raise RuntimeError('Não foi possível preparar o áudio local: ' + (result.stderr or result.stdout)[-400:])
        source = Path(tmp) / 'audio.mp3'
        if not source.exists():
            raise RuntimeError('Áudio não encontrado após conversão.')
        import shutil
        shutil.copyfile(source, target)
    return target

def fetch_audio_and_analyze(url, cache_dir, analyze_func):
    video_id = video_id_from_url(url)
    cache_file = cache_dir / ("youtube_" + video_id + ".json")
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    if not YTDLP.is_file():
        raise RuntimeError("yt-dlp não encontrado no computador.")
    canonical = "https://www.youtube.com/watch?v=" + video_id
    info = {}
    duration = 0
    title = 'Vídeo do YouTube'
    # Evita a chamada adicional --dump-single-json, que pode demorar minutos.
    with tempfile.TemporaryDirectory(prefix="musicsense_yt_") as temp:
        output = str(Path(temp) / "audio.%(ext)s")
        cmd = [str(YTDLP), "--ignore-config", "--no-playlist", "--no-warnings",
            "--max-filesize", "100M", "-f", "bestaudio/best",
            "-x", "--audio-format", "mp3", "--audio-quality", "7",
            "--ffmpeg-location", str(FFMPEG), "-o", output, canonical]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if result.returncode:
            raise RuntimeError("Não foi possível obter o áudio: " + (result.stderr or result.stdout)[-550:])
        files = list(Path(temp).glob("audio.*"))
        if not files:
            raise RuntimeError("O áudio não foi criado.")
        data = analyze_func(str(files[0]), "en")
    data["video_id"] = video_id
    data["title"] = title if title != 'Vídeo do YouTube' else 'YouTube • '+video_id
    data["artist"] = info.get('artist') or info.get('uploader') or ''
    data["duration"] = duration
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data

[executed on device: ESCRITORIO (015f09d9-8ae6-4cef-a39b-c7592204d204)]
