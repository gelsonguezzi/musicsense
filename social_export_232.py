"""MusicSense 232: Instagram feed/reels and original clip presets.
Videos use a dedicated canvas; original audio and entire picture preserved.
For subtitle exports, original and translated lines render in lower safe panel.
"""
import json, math, re, subprocess, tempfile, uuid
from pathlib import Path
from studio_export import ass_escape, ass_time
from cover_card_222 import _wrap_caption
from youtube_support import media_from_url, FFMPEG, YTDLP

FF=Path(FFMPEG)/"ffmpeg.exe"
PROBE=Path(FFMPEG)/"ffprobe.exe"
SIZES={"reels":(1080,1920),"feed":(1080,1350),"square":(1080,1080)}
COLORS={"blue":"0x101f4b","dark":"0x0d1426"}
_ALLOWED_FIT={"blur","blue","dark"}
_ALLOWED_PLACEMENT={"below","overlay"}

def report(cb,percent,step):
    if cb:cb(max(1,min(99,int(percent))),step)

def inspect(path):
    cmd=[str(PROBE),"-v","error","-show_entries",
         "format=duration:stream=width,height,codec_type","-of","json",str(path)]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=25)
    if r.returncode:raise RuntimeError("Falha ao inspecionar video: "+r.stderr[-180:])
    meta=json.loads(r.stdout)
    sizes=[(int(s["width"]),int(s["height"])) for s in meta.get("streams",[])
           if s.get("codec_type")=="video" and s.get("width") and s.get("height")]
    if not sizes:raise ValueError("O arquivo nao contem imagem")
    return float(meta.get("format",{}).get("duration") or 0),sizes[0]

def get_source(url,cache,progress=None):
    media_from_url(url)
    # O gerenciador verifica integridade do cache e tentativas alternativas.
    # Nunca confia apenas no tamanho de um MP4 parcialmente baixado.
    from video_fetch_233 import download
    report(progress,3,"Obtendo videoclipe original")
    result=download(url,cache,
      progress=lambda n,s:report(progress,max(2,min(48,n*.48)),s))
    source=cache/Path(result).name
    if not source.is_file():raise RuntimeError("Download nao produziu videoclipe")
    return source

def wrap(lines,width,size):
    text=ass_escape(lines or "").strip()
    if not text:return ""
    wrapped,scaled=_wrap_caption(text,width,size)
    return r"{\fs"+str(int(scaled))+"}"+wrapped

def subtitles(segments,w,h,placement,video_bottom,temp):
    if not isinstance(segments,list) or not segments or len(segments)>500:
        raise ValueError("Traduza a musica antes de exportar com legendas")
    panel_top=video_bottom+round(h*.018)
    # Reels: safe space above Instagram's caption and action UI.
    panel_bottom=min(h-round(h*.18),h-80) if h>w else h-round(h*.10)
    if placement=="overlay":
        original_y=int(h*.76);translation_y=int(h*.86)
    else:
        original_y=int(panel_top+max(0,panel_bottom-panel_top)*.30)
        translation_y=int(min(panel_bottom-35,original_y+max(85,min(135,round(w*.10)))))
    # Constrain captions independently; do not overlap original video.
    width_limit=int(w*.84)
    english_size=max(30,int(w*.043))
    portuguese_size=max(28,int(w*.039))
    header=f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Original,Arial,{english_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,5,45,45,45,1
Style: Portuguese,Arial,{portuguese_size},&H0058D9FF,&H0058D9FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,5,45,45,45,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogues=[]
    for seg in segments:
        try:
            start,end=float(seg["start"]),float(seg["end"])
            if not 0<=start<end<=3600:continue
            orig=wrap(seg.get("original"),width_limit,english_size)
            trans=wrap(seg.get("translation"),width_limit,portuguese_size)
            # The panel is designed for two lines each, not overlapping the video.
            for style,text,y in (("Original",orig,original_y),("Portuguese",trans,translation_y)):
                if text:
                    dialogues.append(
                        f"Dialogue: 0,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,"
                        +r"{\an5\pos("+f"{w//2},{y}"+r")}"+text)
        except (ValueError,TypeError,KeyError):continue
    if not dialogues:raise ValueError("Nenhuma legenda valida")
    path=temp/"social.ass"
    path.write_text(header+"\n".join(dialogues)+"\n",encoding="utf-8-sig")
    return path

def filters(w,h,source_dimensions,placement,background,has_subs):
    sw,sh=source_dimensions
    # Image keeps natural aspect ratio and fills width when the source allows.
    # For 16:9 material on a vertical canvas this means 1080px wide with zero sidebars.
    natural_height=w*sh/sw
    cap=h if (not has_subs or placement=="overlay") else round(h*.60)
    picture_height=max(2,int(min(natural_height,cap))//2*2)
    scaled=f"scale={w}:{picture_height}:force_original_aspect_ratio=decrease,setsar=1"
    y="0" if has_subs and placement=="below" else "(H-h)/2"
    if background=="blur":
        full=(f"[0:v]split=2[bgsource][mainsource];"
              f"[bgsource]scale={w}:{h}:force_original_aspect_ratio=increase,"
              f"crop={w}:{h},boxblur=luma_radius=28:luma_power=1[bg];"
              f"[mainsource]{scaled}[fg];"
              f"[bg][fg]overlay=(W-w)/2:{y}:shortest=1")
    else:
        color=COLORS[background]
        full=(f"color=c={color}:s={w}x{h}:r=25[bg];"
              f"[0:v]{scaled}[fg];"
              f"[bg][fg]overlay=(W-w)/2:{y}:shortest=1")
    if has_subs and placement=="below":
        # Opaque readable lyric panel, independent of the music video.
        full+=f",drawbox=x=0:y={picture_height}:w=iw:h=ih-{picture_height}:color=0x081225@0.90:t=fill"
    full+=",format=yuv420p"
    return full,picture_height

def render(url,cache,preset="reels",with_lyrics=True,segments=None,
           background="blur",placement="below",progress=None):
    if preset not in (*SIZES,"original"):raise ValueError("Formato nao suportado")
    if background not in _ALLOWED_FIT:raise ValueError("Fundo invalido")
    if placement not in _ALLOWED_PLACEMENT:raise ValueError("Posicao de legendas invalida")
    if not isinstance(with_lyrics,bool):raise ValueError("Configuracao de legendas invalida")
    cache=Path(cache).resolve()
    source=get_source(url,cache,progress).resolve()
    duration,dimensions=inspect(source)
    if not duration or duration>3600:raise ValueError("Duracao de videoclipe invalida")
    if preset=="original" and not with_lyrics:
        report(progress,99,"Videoclipe original pronto, sem recodificacao")
        return "/cache/"+source.name
    if preset=="original":
        # Keep aspect ratio but provide room underneath for captions if requested.
        sw,sh=dimensions
        w=min(1280,max(480,sw));w+=w%2
        h=round(w*sh/sw)
        if with_lyrics and placement=="below":h=round(h*1.40)
        h=max(480,min(1920,h));h+=h%2
    else:w,h=SIZES[preset]
    with tempfile.TemporaryDirectory(prefix="ms_social232_") as folder:
        temp=Path(folder)
        vf,picture_height=filters(w,h,dimensions,placement,background,with_lyrics)
        if with_lyrics:
            ass=subtitles(segments,w,h,placement,picture_height,temp)
            vf+=",subtitles=filename='social.ass'"
        vf+="[v]"
        output=cache/("musicsense_social_"+uuid.uuid4().hex[:12]+".mp4")
        cmd=[str(FF),"-hide_banner","-loglevel","error","-y","-i",str(source),
             "-filter_complex",vf,"-map","[v]","-map","0:a:0?",
             "-c:v","libx264","-preset","veryfast","-crf","23",
             "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k",
             "-movflags","+faststart","-progress","pipe:1","-nostats",
             "-t",str(duration),str(output)]
        report(progress,52,"Montando video vertical e area de legendas")
        proc=subprocess.Popen(cmd,cwd=temp,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              text=True,errors="replace",bufsize=1)
        try:
            last=-1
            for line in proc.stdout:
                if line.startswith(("out_time_ms=","out_time_us=")):
                    try:
                        seconds=int(line.split("=",1)[1])/1_000_000
                        fraction=min(1,max(0,seconds/duration))
                        pct=min(98,52+int(46*fraction))
                        if pct>last:
                            last=pct
                            report(progress,pct,"Renderizando video: "+str(round(100*fraction))+"%")
                    except (ValueError,ZeroDivisionError):pass
            if proc.wait(timeout=120):
                raise RuntimeError("Falha ao renderizar MP4: "+proc.stderr.read()[-700:])
        except Exception:
            output.unlink(missing_ok=True)
            if proc.poll() is None:proc.kill()
            raise
        if not output.is_file() or output.stat().st_size<15000:
            raise RuntimeError("Video nao foi gerado corretamente")
        report(progress,99,"MP4 para redes sociais concluido")
        return "/cache/"+output.name
