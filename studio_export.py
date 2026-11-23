"""Exportação local de MP4 vertical 4:5 com legendas queimadas."""
import json, os, re, subprocess, tempfile, uuid
from pathlib import Path
from email.parser import BytesParser
from email.policy import default

FFMPEG = Path(r"C:\Yt-dlp\ffmpeg.exe")
MAX_SIZE = 100 * 1024 * 1024
def ass_escape(s):
    return str(s).replace('\\','').replace('{','(').replace('}',')').replace('\n',' ')
def ass_time(sec):
    sec=max(0,float(sec))
    hours=int(sec//3600); minutes=int(sec%3600//60); seconds=int(sec%60); centis=int((sec-int(sec))*100)
    return f"{hours}:{minutes:02}:{seconds:02}.{centis:02}"
def make_ass(segments):
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 900
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: English,Arial,32,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,50,50,135,1
Style: Portuguese,Arial,26,&H0065D9FF,&H0065D9FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,50,50,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events=[]
    for seg in segments[:500]:
        try:
            start=float(seg['start']); end=float(seg['end'])
            if not 0<=start<end<=3600:continue
            for style,key in [('English','original'),('Portuguese','translation')]:
                txt=ass_escape(seg.get(key,'')).strip()
                if txt:events.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{txt}")
        except (TypeError,ValueError,KeyError):continue
    if not events:raise ValueError("Não há legendas válidas para exportar.")
    return header+'\n'.join(events)+'\n'
def make_ass_audio_218(segments):
    ass=make_ass(segments)
    ass=ass.replace('Style: English,Arial,32,','Style: English,Arial,55,').replace('Style: Portuguese,Arial,26,','Style: Portuguese,Arial,45,')
    lines=[]
    for line in ass.splitlines():
        if line.startswith('Dialogue: '):
            parts=line.split(',',9)
            if len(parts)==10:
                style=parts[3]
                position=r'{\an5\pos(360,385)}' if style=='English' else r'{\an5\pos(360,505)}'
                parts[9]=position+parts[9]
                line=','.join(parts)
        lines.append(line)
    return '\n'.join(lines)+'\n'

def export_multipart(content_type,payload,cache,progress=None):
    if progress:progress(5,'Recebendo audio e preparando legendas')
    if len(payload)>MAX_SIZE+1000000:raise ValueError('Arquivo excede 100 MB.')
    message=BytesParser(policy=default).parsebytes(('MIME-Version: 1.0\r\nContent-Type: '+content_type+'\r\n\r\n').encode()+payload)
    if not message.is_multipart():raise ValueError('Envio inválido.')
    fields={}
    for part in message.iter_parts():
        name=part.get_param('name',header='content-disposition')
        if name:fields[name]=part
    file=fields.get('file')
    if not file or not file.get_filename():raise ValueError('Escolha um arquivo local autorizado.')
    ext=Path(file.get_filename()).suffix.lower()
    if ext not in ('.mp3','.wav','.m4a','.mp4','.wma','.flac','.ogg'):raise ValueError('Formato não suportado para exportação.')
    blob=file.get_payload(decode=True) or b''
    if len(blob)>MAX_SIZE:raise ValueError('Arquivo excede 100 MB.')
    segpart=fields.get('segments')
    if not segpart:raise ValueError('Legendas ausentes.')
    segments=json.loads(segpart.get_payload(decode=True).decode('utf-8'))
    if not isinstance(segments,list) or len(segments)>500:raise ValueError('Quantidade de legendas inválida.')
    if not FFMPEG.is_file():raise RuntimeError('FFmpeg não encontrado.')
    with tempfile.TemporaryDirectory(prefix='musicsense_export_') as tmp:
        source=Path(tmp)/('input'+ext);source.write_bytes(blob)
        ass=Path(tmp)/'captions.ass';ass.write_text(make_ass(segments) if ext=='.mp4' else make_ass_audio_218(segments),encoding='utf-8-sig')
        out=cache/('musicsense_feed_'+uuid.uuid4().hex[:12]+'.mp4')
        filter_sub='subtitles='+ass.name
        if progress:progress(14,'Legendas preparadas; iniciando codificacao')
        if ext=='.mp4':
            cmd=[str(FFMPEG),'-hide_banner','-loglevel','error','-y','-i',source.name,'-t','360','-vf',f"scale=720:900:force_original_aspect_ratio=decrease,pad=720:900:(ow-iw)/2:(oh-ih)/2:black,{filter_sub}",'-map','0:v:0','-map','0:a:0?','-c:v','libx264','-preset','veryfast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(out)]
        else:
            cmd=[str(FFMPEG),'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','color=c=0x102f9e:s=720x900:r=25','-i',source.name,'-t','360','-shortest','-vf',filter_sub,'-c:v','libx264','-preset','veryfast','-crf','25','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(out)]
        try:
            if progress:
                ffprobe=FFMPEG.with_name('ffprobe.exe')
                meta=subprocess.run([str(ffprobe),'-v','error','-show_entries','format=duration',
                    '-of','default=noprint_wrappers=1:nokey=1',str(source)],
                    capture_output=True,text=True,timeout=15)
                try:duration=min(360,max(.01,float(meta.stdout.strip())))
                except (ValueError,TypeError):duration=360
                cmd[-1:-1]=['-progress','pipe:1','-nostats']
                proc=subprocess.Popen([str(x) for x in cmd],cwd=tmp,stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,text=True,errors='replace')
                try:
                    for line in proc.stdout:
                        if line.startswith('out_time_ms='):
                            try:
                                seconds=int(line.split('=',1)[1])/1000000
                                pct=min(98,14+int(84*min(1,seconds/duration)))
                                progress(pct,'Renderizando MP4: '+str(round(min(100,100*seconds/duration)))+'% do audio')
                            except (ValueError,ZeroDivisionError):pass
                    code=proc.wait(timeout=600)
                    if code:raise RuntimeError('FFmpeg: '+proc.stderr.read()[-600:])
                finally:
                    if proc.poll() is None:proc.kill()
            else:
                r=subprocess.run(cmd,cwd=tmp,capture_output=True,text=True,timeout=600)
                if r.returncode:raise RuntimeError('FFmpeg: '+r.stderr[-600:])
        except subprocess.TimeoutExpired:
            out.unlink(missing_ok=True)
            raise RuntimeError('Exportacao excedeu dez minutos.')
        except Exception:
            out.unlink(missing_ok=True)
            raise
        if not out.exists() or out.stat().st_size<10000:
            out.unlink(missing_ok=True)
            raise RuntimeError('MP4 nao foi criado corretamente')
        if progress:progress(99,'MP4 pronto para salvar')
    return '/cache/'+out.name
