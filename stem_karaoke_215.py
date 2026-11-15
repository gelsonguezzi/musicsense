"""Exporta stems com karaoke local; nao altera os arquivos de audio originais."""
from pathlib import Path
import re,subprocess,uuid
from studio_export import ass_time,ass_escape
FF=Path(r'C:\Yt-dlp\ffmpeg.exe')
def karaoke(seg):
    start=float(seg['start']);end=float(seg['end']);words=seg.get('words') or []
    valid=[w for w in words if isinstance(w,dict) and w.get('text') and isinstance(w.get('start'),(int,float)) and isinstance(w.get('end'),(int,float))]
    if not valid:return ass_escape(seg.get('original',''))
    parts=[];cursor=start
    for w in valid:
        ws=max(start,min(end,float(w['start'])));we=max(ws,min(end,float(w['end'])))
        if ws>cursor:parts.append(r'{\k'+str(max(1,round((ws-cursor)*100)))+'}')
        parts.append(r'{\kf'+str(max(1,round((we-ws)*100)))+'}'+ass_escape(w['text'])+' ')
        cursor=we
    return ''.join(parts).strip()
def subtitles(segments,mode):
    hdr="""[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 0
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Original,Arial,54,&H00FFFFFF,&H0000E5FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,65,65,115,1
Style: Translated,Arial,46,&H0042D7FF,&H0000FFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,65,65,42,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events=[]
    for seg in segments[:500]:
        try:
            st=float(seg['start']);en=float(seg['end'])
            if not 0<=st<en<=3600:continue
            if mode in ('original','both') and seg.get('original'):
                events.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Original,,0,0,0,,{karaoke(seg)}")
            if mode in ('translation','both') and seg.get('translation'):
                # Progresso temporal da frase, sem fingir alinhamento de palavras traduzidas
                length=max(1,round((en-st)*100))
                txt=r'{\kf'+str(length)+'}'+ass_escape(seg['translation'])
                events.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Translated,,0,0,0,,{txt}")
        except (KeyError,TypeError,ValueError):continue
    if not events:raise ValueError('Nao ha legendas para o modo escolhido')
    return hdr+'\n'.join(events)+'\n'
def export(stem,mode,segments,cache,progress=None):
    if mode not in ('original','translation','both'):raise ValueError('Modo invalido')
    if not isinstance(stem,str) or not re.fullmatch(r'/cache/musicsense_(instrumental|vocals)_[0-9a-f]{10}\.mp3',stem):raise ValueError('Faixa invalida')
    source=cache/Path(stem).name
    if not source.is_file():raise ValueError('Faixa nao encontrada. Separe novamente a musica.')
    if not isinstance(segments,list) or not 1<=len(segments)<=500:raise ValueError('Legendas invalidas')
    import tempfile
    with tempfile.TemporaryDirectory(prefix='ms_stem_') as tmp:
        ass=Path(tmp)/'karaoke.ass';ass.write_text(subtitles(segments,mode),encoding='utf-8-sig')
        dest=cache/('musicsense_karaoke_'+uuid.uuid4().hex[:12]+'.mp4')
        cmd=[str(FF),'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','color=c=0x141828:s=1280x720:r=25','-i',str(source),'-t','360','-shortest','-vf','subtitles=karaoke.ass','-c:v','libx264','-preset','veryfast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-progress','pipe:1','-nostats',str(dest)]
        if progress:progress(8,'Preparando letras e audio')
        proc=subprocess.Popen(cmd,cwd=tmp,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        for line in proc.stdout:
            if line.startswith('out_time_ms=') and progress:
                try:progress(min(95,10+int(int(line.split('=',1)[1])/1000000/360*85)),'Gerando MP4 com karaoke')
                except (ValueError,ZeroDivisionError):pass
        err=proc.stderr.read()
        if proc.wait()!=0 or not dest.is_file():raise RuntimeError('FFmpeg: '+err[-500:])
        if progress:progress(100,'Concluido')
        return '/cache/'+dest.name
