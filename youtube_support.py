"""Integração local de links YouTube. Não modifica C:\\Yt-dlp."""
import hashlib
import json
import re
import subprocess
import tempfile
import shutil
from pathlib import Path
from urllib.parse import urlparse, parse_qs

YTDLP = Path(r"C:\Yt-dlp\yt-dlp.exe") if Path(r"C:\Yt-dlp\yt-dlp.exe").is_file() else Path(shutil.which("yt-dlp") or "yt-dlp")
FFMPEG = Path(r"C:\Yt-dlp") if (Path(r"C:\Yt-dlp")/"ffmpeg.exe").is_file() else Path(shutil.which("ffmpeg") or "ffmpeg").parent
MAX_DURATION = 900

def media_from_url(url):
    """Validate a supported public clip URL and return its canonical identity."""
    try:
        parsed = urlparse(str(url).strip())
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password or parsed.port:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Use um link válido do YouTube ou Instagram.")
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"):
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("ID de vídeo inválido.")
        return {"platform": "youtube", "id": video_id,
                "canonical": "https://www.youtube.com/watch?v=" + video_id,
                "cache_id": video_id}
    if host == "youtu.be":
        video_id = parts[0] if parts else ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("ID de vídeo inválido.")
        return {"platform": "youtube", "id": video_id,
                "canonical": "https://www.youtube.com/watch?v=" + video_id,
                "cache_id": video_id}
    if host in ("instagram.com", "www.instagram.com", "m.instagram.com"):
        kind = parts[0].lower() if parts else ""
        shortcode = parts[1] if len(parts) > 1 else ""
        if kind in ("p", "reel", "reels", "tv") and re.fullmatch(r"[A-Za-z0-9_-]{5,80}", shortcode):
            kind = "reel" if kind == "reels" else kind
            return {"platform": "instagram", "id": shortcode,
                    "canonical": f"https://www.instagram.com/{kind}/{shortcode}/",
                    "cache_id": "instagram_" + shortcode}
    raise ValueError("Use o link de um vídeo do YouTube ou de um post/Reel público do Instagram.")

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


def fetch_manual_captions(video_id, cache_dir):
    """Prefer creator-supplied captions. Never use automatic captions as authoritative."""
    import html
    from datetime import timedelta
    canonical='https://www.youtube.com/watch?v='+video_id
    with tempfile.TemporaryDirectory(prefix='musicsense_caps_') as tmp:
        cmd=[str(YTDLP),'--ignore-config','--skip-download','--write-subs',
             '--sub-langs','en.*,es.*,it.*,pt.*','--sub-format','vtt',
             '-o',str(Path(tmp)/'captions.%(ext)s'),canonical]
        try:
            proc=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
            files=list(Path(tmp).glob('captions.*.vtt'))
            if proc.returncode or not files:return None
            files.sort(key=lambda f: (0 if '.en' in f.name else 1 if '.es' in f.name else 2 if '.it' in f.name else 3))
            vtt=files[0].read_text(encoding='utf-8-sig')
            lang=files[0].name.split('.')[1].split('-')[0]
            def seconds(st):
                parts=st.split(':')
                return round(sum(float(x)*60**i for i,x in enumerate(reversed(parts))),3)
            result=[]
            for block in re.split(r'\n\s*\n',vtt):
                lines=[x.strip() for x in block.splitlines() if x.strip()]
                stamp=next((i for i,x in enumerate(lines) if '-->' in x),None)
                if stamp is None:continue
                start,end=lines[stamp].split('-->',1)
                end=end.strip().split()[0]
                text=' '.join(lines[stamp+1:])
                text=re.sub(r'<[^>]*>','',text)
                text=html.unescape(text)
                text=re.sub(r'[♪♫♬]+','',text).strip()
                if not text or (text.startswith('(') and text.endswith(')')) or (text.startswith('[') and text.endswith(']')):continue
                a,b=seconds(start.strip()),seconds(end)
                if b<=a:continue
                result.append({'start':a,'end':b,'original':text,'words':[]})
            if len(result)<12:return None
            # Split overly long captions only at punctuation, never fabricate word timing.
            from server import translate_lines
            translated,engine=translate_lines([x['original'] for x in result],lang)
            for seg,pt in zip(result,translated):seg['translation']=pt
            return {'language':lang,'translation_engine':engine,'segments':result,
                    'audio_duration':round(max(x['end'] for x in result),2),
                    'caption_source':'youtube_manual'}
        except Exception as exc:
            print('[CAPTIONS] Falha:',exc,flush=True)
            return None

def fetch_audio_and_analyze(url, cache_dir, analyze_func, progress=None):
    video_id = video_id_from_url(url)
    cache_file = cache_dir / ("youtube_" + video_id + ".json")
    if progress:progress(6,'Verificando musica ja analisada')
    if cache_file.exists():
        cached=json.loads(cache_file.read_text(encoding='utf-8'))
        if cached.get('karaoke_schema')==4 and len(cached.get('segments',[]))>=4:
            if cached.get('language')=='it' and any(not x.get('translation') for x in cached['segments']):
                from server import translate_lines
                pts,engine=translate_lines([x['original'] for x in cached['segments']],'it')
                for x,pt in zip(cached['segments'],pts):x['translation']=pt
                cached['translation_engine']=engine
                cache_file.write_text(json.dumps(cached,ensure_ascii=False),encoding='utf-8')
            if progress:progress(98,'Analise recuperada do cache')
            return cached
    if not YTDLP.is_file():
        raise RuntimeError("yt-dlp não encontrado no computador.")
    canonical = "https://www.youtube.com/watch?v=" + video_id
    info = {}
    duration = 0
    title = 'Vídeo do YouTube'
    # Reutiliza áudio autorizado já baixado; não repetir download a cada ajuste.
    audio_file=cache_dir / ('youtube_'+video_id+'.mp3')
    if progress:progress(9,'Preparando audio do YouTube')
    if not audio_file.is_file() or audio_file.stat().st_size<10000:
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
            if not files: raise RuntimeError("O áudio não foi criado.")
            import shutil
            shutil.copyfile(files[0],audio_file)
    if progress:progress(12,'Iniciando analise e traducao')
    manual=fetch_manual_captions(video_id,cache_dir)
    data = manual or analyze_func(str(audio_file), None, progress=progress)
    if manual and progress:progress(90,'Legendas existentes localizadas')
    data['karaoke_schema']=4
    data["video_id"] = video_id
    data["title"] = title if title != 'Vídeo do YouTube' else 'YouTube • '+video_id
    data["artist"] = info.get('artist') or info.get('uploader') or ''
    data["duration"] = duration
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    if progress:progress(99,'Guardando analise')
    return data
