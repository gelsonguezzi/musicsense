"""MusicSense 227: exporta stems selecionados no mixer e MP4 legendado.
Nao altera audios separados. Usa apenas arquivos ja gerados em /cache.
"""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile

from studio_export import ass_time, ass_escape
from cover_card_222 import _wrap_caption

BASE = Path(__file__).resolve().parent
FF = Path(r"C:\Yt-dlp\ffmpeg.exe")
FP = Path(r"C:\Yt-dlp\ffprobe.exe")
YTDLP = Path(r"C:\Yt-dlp\yt-dlp.exe")
STEM = re.compile(r"^/cache/musicsense_stem_(?:lead_vocals|vocals|backing_vocals|drums|kick|snare|cymbals|toms|bass|guitar|piano|other)_[a-f0-9]{10}\.mp3$")
FORMATS = {"1:1": (960, 960), "16:9": (1280, 720), "9:16": (720, 1280)}
MAX_LENGTH = 360


def report(cb, value, message):
    if cb:
        cb(min(99, max(1, round(value))), message)


def probe(path):
    cmd = [str(FP), "-v", "error", "-show_entries",
           "format=duration:stream=width,height", "-of", "json", str(path)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if p.returncode:
        raise RuntimeError("Erro ao verificar arquivo de audio/video")
    data = json.loads(p.stdout)
    duration = float(data.get("format", {}).get("duration") or 0)
    sizes = [(int(s["width"]), int(s["height"])) for s in data.get("streams", [])
             if s.get("width") and s.get("height")]
    return duration, (sizes[0] if sizes else None)


def selected(request, cache):
    items = request.get("selected")
    if not isinstance(items, list) or not 1 <= len(items) <= 10:
        raise ValueError("Ative S em uma ou mais trilhas (maximo 10).")
    known = set()
    chosen = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Trilha invalida")
        url = item.get("url")
        if not isinstance(url, str) or not STEM.fullmatch(url):
            raise ValueError("Arquivo de trilha nao autorizado")
        if url in known:
            raise ValueError("Trilhas repetidas")
        known.add(url)
        path = cache / Path(url).name
        if not path.is_file() or path.stat().st_size < 10000:
            raise ValueError("Uma trilha nao esta mais disponivel. Abra novamente a mesa.")
        vol = float(item.get("volume", .8))
        if not 0 <= vol <= 1:
            raise ValueError("Volume deve estar entre 0 e 100%")
        label = str(item.get("label") or Path(url).stem).strip()[:55]
        chosen.append({"path": path, "url": url, "volume": vol,
                       "label": label, "key": Path(url).stem[16:].rsplit("_", 1)[0]})
    return chosen


def mixed_audio(selected_tracks, target, progress=None, effects=None):
    count = len(selected_tracks)
    cmd = [str(FF), "-hide_banner", "-loglevel", "error", "-y"]
    filters = []
    parts = []
    for index, stem in enumerate(selected_tracks):
        cmd.extend(["-i", str(stem["path"])])
        vol = float(stem["volume"])
        chain = f"[{index}:a]aresample=async=1:first_pts=0,volume={vol:.4f}"
        if stem["key"] in ("vocals", "lead_vocals") and effects:
            if effects.get("echo"):
                chain += ",aecho=0.78:0.68:175:0.27"
            if effects.get("reverb"):
                chain += ",aecho=0.85:0.65:42|78:0.16|0.11"
        chain += f"[s{index}]"
        filters.append(chain)
        parts.append(f"[s{index}]")
    if count == 1:
        filters.append(f"[s0]alimiter=limit=0.96[m]")
    else:
        filters.append("".join(parts) +
                       f"amix=inputs={count}:duration=shortest:dropout_transition=0:normalize=1,"
                       "alimiter=limit=0.96[m]")
    cmd.extend(["-filter_complex", ";".join(filters), "-map", "[m]",
                "-t", str(MAX_LENGTH), "-c:a", "libmp3lame", "-q:a", "1",
                "-progress", "pipe:1", "-nostats", str(target)])
    report(progress, 8, "Mixando trilhas selecionadas")
    duration = min(MAX_LENGTH, min(probe(s["path"])[0] for s in selected_tracks))
    execute(cmd, max(duration, 1), progress, 10, 47, "Mixando audio")
    if not target.is_file() or target.stat().st_size < 10000:
        raise RuntimeError("A mixagem MP3 nao foi gerada")
    return duration


def execute(cmd, duration, progress, start, finish, label, cwd=None, timeout=720):
    process = subprocess.Popen([str(x) for x in cmd], cwd=cwd,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, errors="replace", bufsize=1)
    begin = time.monotonic()
    last = -1
    try:
        for line in process.stdout:
            if time.monotonic() - begin > timeout:
                process.kill()
                raise RuntimeError("Tempo de renderizacao excedido")
            if line.startswith(("out_time_ms=", "out_time_us=")):
                try:
                    value = int(line.split("=", 1)[1]) / 1_000_000
                    pct = min(finish, start + (finish-start)*min(1, value/max(.1, duration)))
                    if int(pct) > last:
                        last = int(pct)
                        report(progress, pct, f"{label} • {min(100,round(100*value/duration))}%")
                except (ValueError, ZeroDivisionError):
                    pass
        if process.wait(timeout=120):
            raise RuntimeError("Erro do FFmpeg: " + process.stderr.read()[-850:])
    finally:
        if process.poll() is None:
            process.kill()


def ass(segments, width, height, temp):
    if not isinstance(segments, list) or not 1 <= len(segments) <= 500:
        raise ValueError("Analise e traduza a musica antes de salvar MP4")
    original_size = max(28, min(60, int(width*.052)))
    translated_size = max(25, min(49, int(width*.043)))
    pos_x = width//2
    pos_o = int(height*.73)
    pos_t = int(height*.895)
    border = max(2, round(width/350))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Original,Arial,{original_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{border},1,5,45,45,60,1
Style: Translation,Arial,{translated_size},&H0059D9FF,&H0059D9FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{border},1,5,45,45,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for seg in segments:
        try:
            st, en = float(seg["start"]), float(seg["end"])
            if not 0 <= st < en <= 3600:
                continue
            for style, name, size, y, k in [
                ("Original", "original", original_size, pos_o, "original"),
                ("Translation", "translation", translated_size, pos_t, "translation")]:
                text = ass_escape(seg.get(k, ""))
                if not text.strip():
                    continue
                wrapped, fitted = _wrap_caption(text, width*.79, size)
                events.append(
                    f"Dialogue: 0,{ass_time(st)},{ass_time(en)},{style},,0,0,0,,"
                    + r"{\an5\pos(" + f"{pos_x},{y}" + r")\fs" + str(fitted) + "}" + wrapped
                )
        except (TypeError, KeyError, ValueError):
            continue
    if not events:
        raise ValueError("Nenhuma legenda valida para o MP4")
    path = temp / "mixer_227.ass"
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")
    return path


def source_video(url, target, progress):
    from youtube_support import video_id_from_url
    video_id = video_id_from_url(url)
    canonical = "https://www.youtube.com/watch?v=" + video_id
    if not YTDLP.is_file():
        raise RuntimeError("Ferramenta de video indisponivel")
    command = [str(YTDLP), "--ignore-config", "--no-warnings", "--no-playlist",
               "--max-filesize", "100M", "--ffmpeg-location", str(FF),
               "-f", "bv*[height<=720]/b[height<=720]", "--merge-output-format", "mp4",
               "-o", str(target.parent / "background.%(ext)s"), canonical]
    report(progress, 49, "Obtendo videoclipe original")
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise RuntimeError("Videoclipe indisponivel: "+(result.stderr or result.stdout)[-450:])
    files = [f for f in target.parent.glob("background.*")
             if f.suffix.lower() in (".mp4", ".webm", ".mkv")]
    if not files:
        raise RuntimeError("Videoclipe nao foi baixado")
    source = max(files, key=lambda p: p.stat().st_size)
    if source.stat().st_size > 100*1024*1024:
        raise RuntimeError("O videoclipe excede 100 MB")
    return source


def output_format(request, video):
    shape = str(request.get("format", "original"))
    if shape not in (*FORMATS, "original"):
        raise ValueError("Formato de video invalido")
    if shape != "original":
        return FORMATS[shape]
    if video:
        _, dimensions = probe(video)
        if dimensions:
            width, height = dimensions
            scale = min(1.0, 1280/max(1,width), 1280/max(1,height))
            w, h = int(width*scale)//2*2, int(height*scale)//2*2
            return max(320, w), max(240, h)
    return FORMATS["16:9"]


def export(request, cache, progress=None):
    if request.get("mode") not in ("zip", "mp4"):
        raise ValueError("Modo de exportacao invalido")
    chosen = selected(request, cache)
    mode = request["mode"]
    effects = request.get("effects", {}) if isinstance(request.get("effects", {}), dict) else {}
    with tempfile.TemporaryDirectory(prefix="ms_mixer_export227_") as tmp:
        temp = Path(tmp)
        mixed = temp / "mixagem.mp3"
        duration = mixed_audio(chosen, mixed, progress, effects=effects)
        if mode == "zip":
            target = cache / ("musicsense_multitrilhas_"+uuid.uuid4().hex[:12]+".zip")
            report(progress, 71, "Organizando arquivos individuais")
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as bundle:
                bundle.write(mixed, "MusicSense_Mixagem.mp3")
                for ix, item in enumerate(chosen):
                    filename = re.sub(r"[^A-Za-z0-9_-]+", "_", item["label"])[:45]
                    bundle.write(item["path"], f"Trilhas/{ix+1:02d}_{filename}.mp3")
                    report(progress, 72+23*(ix+1)/len(chosen),
                           "Adicionando trilha "+str(ix+1)+"/"+str(len(chosen)))
                bundle.writestr("LEIA-ME.txt",
                    "MusicSense - Multi-trilhas\nTrilhas escolhidas com S ativo.\n"
                    "Inclui MP3s separados e uma mixagem com volumes/effects atuais.\n"
                    "Arquivos originais permanecem preservados.\n")
            report(progress, 99, "ZIP pronto")
            return {"url":"/cache/"+target.name, "filename":"MusicSense_Multitrilhas.zip"}
        background = request.get("background", "blue")
        if background not in ("blue", "video"):
            raise ValueError("Fundo invalido")
        video = None
        if background == "video":
            video = source_video(str(request.get("youtube_url") or ""),temp/"background.mp4",progress)
        width,height = output_format(request, video)
        assfile = ass(request.get("segments"), width, height, temp)
        report(progress, 52, "Compondo videoclipe com dois idiomas")
        target = cache / ("musicsense_mix_karaoke_"+uuid.uuid4().hex[:12]+".mp4")
        cmd = [str(FF), "-hide_banner", "-loglevel", "error", "-y",
               "-i", str(mixed)]
        if video:
            cmd.extend(["-i", str(video)])
        else:
            cmd.extend(["-f", "lavfi", "-i",
                        f"color=c=0x122d82:s={width}x{height}:r=25"])
        filter_video = (
            f"[1:v]fps=25,scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,format=yuv420p,subtitles={assfile.name}[v]"
        )
        cmd.extend(["-filter_complex", filter_video, "-map", "[v]", "-map", "0:a:0",
                    "-t", str(duration), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "192k", "-movflags", "+faststart",
                    "-progress", "pipe:1", "-nostats", str(target)])
        try:
            execute(cmd, duration, progress, 54, 98,
                    "Gerando MP4 com legendas", cwd=temp, timeout=720)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        if not target.is_file() or target.stat().st_size < 20000:
            raise RuntimeError("O MP4 nao foi gerado")
        report(progress, 99, "MP4 pronto")
        return {"url":"/cache/"+target.name, "filename":"MusicSense_Mixagem_Legendada.mp4"}
