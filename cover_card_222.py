"""Capa cinematografica e MP4 com duas legendas, MusicSense 222."""
import json
import re
import subprocess
import urllib.request
import uuid
from pathlib import Path

from studio_export import make_ass

FFMPEG = Path(r"C:\Yt-dlp\ffmpeg.exe")
FFPROBE = Path(r"C:\Yt-dlp\ffprobe.exe")
YTDLP = Path(r"C:\Yt-dlp\yt-dlp.exe")


def _run(args, cwd=None, timeout=90):
    result = subprocess.run([str(x) for x in args], cwd=cwd, capture_output=True,
                            text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("FFmpeg: " + (result.stderr or result.stdout)[-800:])
    return result


def _dimensions(image):
    try:
        output = _run([FFPROBE, "-v", "error", "-select_streams", "v:0",
                       "-show_entries", "stream=width,height", "-of", "json", image], timeout=12)
        stream = json.loads(output.stdout)["streams"][0]
        return int(stream["width"]), int(stream["height"])
    except Exception:
        return 0, 0


def _picture_width(source):
    """Largura util em pixels do clipe 1280x720, inclusive faixas embutidas."""
    w,h=_dimensions(source)
    if not w or not h:
        return 960
    drawn_width=min(1280,int(720*w/max(h,1)))
    try:
        result=subprocess.run([str(FFMPEG),"-hide_banner","-loglevel","info",
          "-ss","12","-i",str(source),"-an",
          "-vf","cropdetect=limit=24:round=2:reset=0",
          "-frames:v","22","-f","null","NUL"],
          capture_output=True,text=True,timeout=35)
        crops=[(int(a),int(x)) for a,x in re.findall(r"crop=(\d+):\d+:(\d+):\d+",result.stderr)]
        usable=[width for width,x in crops if width>=w*.48 and abs((w-width)/2-x)<w*.075]
        if len(usable)>=5:
            measured=sorted(usable)[len(usable)//2]
            return min(drawn_width,int(drawn_width*measured/w))
    except Exception:
        pass
    return drawn_width


def _photo(video_id, source, temp):
    """Prefere foto real do videoclipe; nao aceita miniaturas falsas de 120 px."""
    for quality in ("maxresdefault", "sddefault", "hqdefault", "mqdefault"):
        url = f"https://i.ytimg.com/vi/{video_id}/{quality}.jpg"
        candidate = temp / ("yt_" + quality + ".jpg")
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=9) as response:
                if not response.headers.get("Content-Type", "").startswith("image/"):
                    continue
                image_data = response.read(6 * 1024 * 1024)
            if len(image_data) < 12000:
                continue
            candidate.write_bytes(image_data)
            width, height = _dimensions(candidate)
            if width >= 640 and height >= 360:
                return candidate
        except Exception:
            continue
    # Evita o primeiro segundo do clipe, que frequentemente e um fade preto.
    for second in (12, 6, 22, 2):
        candidate = temp / f"video_frame_{second}.jpg"
        try:
            _run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                  "-ss", str(second), "-i", source, "-frames:v", "1", candidate],
                 timeout=35)
            if candidate.exists() and candidate.stat().st_size > 10000:
                return candidate
        except Exception:
            continue
    raise RuntimeError("Nao foi possivel selecionar uma foto para a capa.")


def _title_parts(raw_title, video_id):
    title = str(raw_title or "").strip()
    if not title or title.lower().startswith("youtube "):
        try:
            r = _run([YTDLP, "--ignore-config", "--no-warnings", "--skip-download",
                      "--print", "%(title)s",
                      "https://www.youtube.com/watch?v=" + video_id], timeout=35)
            title = r.stdout.strip().splitlines()[-1]
        except Exception:
            pass
    title = re.sub(r"(?i)\s*[\[(](?:official|music video|lyric video|lyrics?|hd|4k|audio)"
                   r"[^\])]*[\])]", "", title).strip()
    parts = re.split(r"\s+[-–—]\s+", title, maxsplit=1)
    if len(parts) == 2:
        return parts[0][:115], parts[1][:150]
    artist = "MusicSense AI"
    try:
        r = _run([YTDLP, "--ignore-config", "--no-warnings", "--skip-download",
                  "--print", "%(uploader)s",
                  "https://www.youtube.com/watch?v=" + video_id], timeout=35)
        if r.stdout.strip():
            artist = r.stdout.strip().splitlines()[-1]
    except Exception:
        pass
    return artist[:115], (title or "Videoclipe")[:150]


def _translated_song(song, language):
    try:
        from server import translate_lines
        translations, _ = translate_lines([song], str(language or "en").split("-")[0])
        result = str(translations[0] or "").strip()
        return result if result.casefold() != song.casefold() else ""
    except Exception:
        return ""


def _font_size(text, preferred, minimum, width=1100):
    # Largura media de caracteres em Arial Bold. Mantem uma linha e evita cortes.
    count = max(1, len(text))
    return max(minimum, min(preferred, int(width / (count * .59))))


def _make_card(photo, temp, artist, song, translated):
    for name, text in (("artist", artist), ("song", song), ("translation", translated)):
        (temp / (name + ".txt")).write_text(text[:160], encoding="utf-8")
    # Usa FFmpeg para gerar UMA imagem de capa real, que sera o frame zero.
    font = r"C\:/Windows/Fonts/arialbd.ttf"
    artist_size = _font_size(artist, 37, 19)
    song_size = _font_size(song, 54, 23)
    translation_size = _font_size(translated, 32, 17)
    caption = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1280:720:force_original_aspect_ratio=increase,"
        "crop=1280:720,boxblur=24:2,eq=brightness=-0.19[background];"
        "[fg]scale=1280:720:force_original_aspect_ratio=decrease[front];"
        "[background][front]overlay=(W-w)/2:(H-h)/2,"
        "drawbox=x=0:y=418:w=iw:h=302:color=black@0.73:t=fill,"
        "drawbox=x=0:y=419:w=iw:h=4:color=0xB18EFF@0.95:t=fill,"
        f"drawtext=fontfile='{font}':textfile='artist.txt':"
        f"fontsize={artist_size}:fontcolor=0xffdf90:x=(w-text_w)/2:y=461:fix_bounds=1,"
        f"drawtext=fontfile='{font}':textfile='song.txt':"
        f"fontsize={song_size}:fontcolor=white:x=(w-text_w)/2:y=521:fix_bounds=1,"
        f"drawtext=fontfile='{font}':textfile='translation.txt':"
        f"fontsize={translation_size}:fontcolor=0xffd277:x=(w-text_w)/2:y=622:fix_bounds=1"
    )
    frame = temp / "music_cover_222.png"
    _run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", photo,
          "-filter_complex", caption, "-frames:v", "1", frame], cwd=temp, timeout=90)
    if not frame.exists() or _dimensions(frame) != (1280, 720):
        raise RuntimeError("Falha ao produzir a capa em alta qualidade.")
    return frame


def _wrap_caption(text, max_width=1090, normal_size=60):
    """Divide no maximo em duas linhas, centralizadas e dentro da area segura."""
    words = " ".join(str(text).split()).split(" ")
    if not words or words == [""]:
        return "", normal_size
    def visual_units(value):
        # Estimativa conservadora para Arial Bold. Letras estreitas ocupam menos.
        return sum(.36 if ch in "ilI.,:;!|' " else .78 if ch in "MW@%#&" else .56 for ch in value)
    full = " ".join(words)
    if visual_units(full) * normal_size <= max_width:
        lines = [full]
    else:
        options = [(" ".join(words[:i]), " ".join(words[i:]))
                   for i in range(1, len(words))]
        if options:
            lines = list(min(options, key=lambda pair: (
                max(visual_units(pair[0]), visual_units(pair[1])),
                abs(visual_units(pair[0]) - visual_units(pair[1]))
            )))
        else:
            lines = [full]
    # Em frases excepcionais, preserva as duas linhas e reduz a fonte,
    # nunca extrapolando a margem de seguranca de 95 px em ambos os lados.
    longest = max(visual_units(line) for line in lines)
    size = min(normal_size, max(14, int(max_width / max(longest, .1))))
    return r"\N".join(lines), size


def _captions(segments, temp, safe_width=890):
    ass = make_ass(segments)
    ass = ass.replace("PlayResX: 720", "PlayResX: 1280")
    ass = ass.replace("PlayResY: 900", "PlayResY: 720")
    # Base mantida em +20%: tamanho 60 para original e 52 para traducao.
    ass = ass.replace("Style: English,Arial,32,", "Style: English,Arial,60,")
    ass = ass.replace("Style: Portuguese,Arial,26,", "Style: Portuguese,Arial,52,")
    ass = ass.replace("50,50,135,1", "100,100,167,1")
    ass = ass.replace("50,50,70,1", "100,100,48,1")
    fixed = []
    for row in ass.splitlines():
        if row.startswith("Dialogue: "):
            parts = row.split(",", 9)
            if len(parts) == 10:
                style = parts[3]
                base_size = 60 if style == "English" else 52
                wrapped, size = _wrap_caption(parts[9], safe_width, base_size)
                # Original fica no centro inferior; traducao abaixo dela.
                # As duas areas reservadas nao se sobrepoem em duas linhas.
                y = 405 if style == "English" else 608
                parts[9] = r"{\an5\pos(640," + str(y) + r")\fs" + str(size) + "}" + wrapped
                row = ",".join(parts)
        fixed.append(row)
    path = temp / "captions.ass"
    path.write_text("\n".join(fixed) + "\n", encoding="utf-8-sig")
    return path


def render_captioned_video(source, cache, temp, video_id, segments, title, language, progress=None):
    if progress:progress(43,'Preparando imagem de capa e titulo da musica')
    artist, song = _title_parts(title, video_id)
    translated = _translated_song(song, language)
    photo = _photo(video_id, source, temp)
    cover = _make_card(photo, temp, artist, song, translated)
    # Limita as legendas a area da imagem, nao as faixas pretas laterais.
    picture_w=_picture_width(source)
    # Limite seguro mesmo quando a fonte ja tem faixas pretas embutidas
    # ou o clipe curto nao permite analisar a borda por cropdetect.
    safe_width=max(180,min(820,picture_w-140))
    captions = _captions(segments, temp, safe_width=safe_width)
    if progress:progress(49,'Capa e legendas prontas; iniciando renderizacao')
    output = cache / ("musicsense_video_" + uuid.uuid4().hex[:12] + ".mp4")
    graph = (
        "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,setsar=1,"
        "subtitles=" + captions.name + "[main];"
        "[1:v]format=yuva420p[card];"
        "[main][card]overlay=0:0:enable='lt(t,2.5)':"
        "eof_action=repeat:format=auto,format=yuv420p[v]"
    )
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
           "-i", source, "-loop", "1", "-framerate", "25", "-i", cover,
           "-t", "360", "-shortest", "-filter_complex", graph,
           "-map", "[v]", "-map", "0:a:0?", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
           "-metadata", "title=" + artist + " - " + song, output]
    try:
        if progress:
            # O tempo real do video exportado determina o percentual da codificacao.
            probe = _run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", source], timeout=15)
            duration = min(360.0, max(.01, float(probe.stdout.strip())))
            cmd[-1:-1] = ["-progress", "pipe:1", "-nostats"]
            proc = subprocess.Popen([str(x) for x in cmd], cwd=temp,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, errors="replace", bufsize=1)
            try:
                for line in proc.stdout:
                    if line.startswith("out_time_ms="):
                        try:
                            sec = int(line.split("=",1)[1]) / 1000000
                            progress(min(98,49+int(49*min(1,sec/duration))),
                                     "Renderizando MP4: " + str(round(min(100,100*sec/duration))) + "% do video")
                        except (ValueError,ZeroDivisionError):
                            pass
                if proc.wait(timeout=600):
                    raise RuntimeError("FFmpeg: "+proc.stderr.read()[-700:])
            finally:
                if proc.poll() is None:proc.kill()
        else:
            _run(cmd, cwd=temp, timeout=600)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    if not output.is_file() or output.stat().st_size < 20000:
        output.unlink(missing_ok=True)
        raise RuntimeError("Arquivo MP4 nao foi produzido corretamente.")
    return "/cache/" + output.name
