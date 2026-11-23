"""Local editor de videoclipes MusicSense 210."""
import json, subprocess, tempfile, uuid, urllib.request, urllib.parse, ipaddress, socket
from pathlib import Path
from email.parser import BytesParser
from email.policy import default
from studio_export import make_ass
from cover_card_222 import _wrap_caption
from youtube_support import fetch_audio_for_playback
FF=Path(r'C:\Yt-dlp\ffmpeg.exe')
FP=Path(r'C:\Yt-dlp\ffprobe.exe')
FORMATS={'16:9':(1280,720),'9:16':(720,1280),'4:5':(720,900)}
def run(args,cwd=None,timeout=120):
    r=subprocess.run([str(FF),'-hide_banner','-loglevel','error','-y']+list(map(str,args)),cwd=cwd,capture_output=True,text=True,timeout=timeout)
    if r.returncode:raise RuntimeError('Falha ao gerar video: '+r.stderr[-350:])
def remote_image(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:raise ValueError('Use URL HTTPS direta de imagem')

    for item in socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(item[4][0]).is_global:raise ValueError('Endereco de rede nao permitido')
    opener=urllib.request.build_opener(urllib.request.HTTPHandler(),urllib.request.HTTPSHandler())
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kw):raise ValueError('Redirecionamento de imagem nao permitido')
    opener.add_handler(NoRedirect())
    with opener.open(urllib.request.Request(url,headers={'User-Agent':'MusicSense/210'}),timeout=15) as r:
        if r.geturl()!=url:raise ValueError('Redirecionamento nao permitido')
        if not r.headers.get('Content-Type','').lower().startswith('image/'):raise ValueError('URL nao retornou imagem')
        blob=r.read(12*1024*1024+1)
        if len(blob)>12*1024*1024:raise ValueError('Imagem excede 12 MB')
        kind=('jpeg' if blob.startswith(bytes.fromhex('ffd8ff')) else 'png' if blob.startswith(bytes.fromhex('89504e470d0a1a0a')) else 'webp' if blob[:4]==b'RIFF' and blob[8:12]==b'WEBP' else None)
        if kind not in ('jpeg','png','webp'):raise ValueError('O link nao retornou uma imagem JPG, PNG ou WebP valida')
        return blob,('.jpg' if kind=='jpeg' else '.'+kind)
def export(content_type,body,cache,progress=None):
    def report(pct,stage):
        if progress:progress(int(pct),stage)
    report(5,"Recebendo e validando arquivos")
    if len(body)>180*1024*1024:raise ValueError('Materiais excedem 180 MB')
    form=BytesParser(policy=default).parsebytes(('MIME-Version: 1.0\r\nContent-Type: '+content_type+'\r\n\r\n').encode()+body)
    if not form.is_multipart():raise ValueError('Formulario invalido')
    parts=list(form.iter_parts()); fields={}
    for part in parts:
        name=part.get_param('name',header='content-disposition')
        if name:fields.setdefault(name,[]).append(part)
    settings=json.loads(fields['settings'][0].get_payload(decode=True))
    segments=settings.get('segments')
    if not isinstance(segments,list) or not 1<=len(segments)<=500:raise ValueError('Legendas invalidas')
    fmt=settings.get('format','16:9')
    if fmt not in FORMATS:raise ValueError('Formato invalido')
    w,h=FORMATS[fmt]
    duration=float(settings.get('duration',0))
    if not 1<=duration<=360:raise ValueError('Duracao deve ser ate 6 minutos')
    entries=settings.get('items',[])
    if not isinstance(entries,list) or not 1<=len(entries)<=20:raise ValueError('Adicione de 1 a 20 materiais')
    fileparts=fields.get('media',[])
    with tempfile.TemporaryDirectory(prefix='musicsense_210_') as tmp:
        root=Path(tmp); sources=[]
        for i,part in enumerate(fileparts):
            ext=Path(part.get_filename() or '').suffix.lower()
            if ext not in ('.jpg','.jpeg','.png','.webp','.mp4','.webm'):raise ValueError('Formato de arquivo nao suportado')
            data=part.get_payload(decode=True) or b''
            if len(data)>100*1024*1024:raise ValueError('Arquivo individual excede 100 MB')
            path=root/f'media_{i}{ext}';path.write_bytes(data);sources.append(path)
        report(12,"Preparando imagens e videos")
        playlist=[]
        for item in entries:
            if item.get('type')=='url':
                try:data,ext=remote_image(str(item.get('url','')))
                except Exception as exc:raise ValueError('Falha ao importar imagem '+str(item.get('url',''))[:85]+': '+str(exc))
                path=root/f'remote_{len(playlist)}{ext}';path.write_bytes(data)
            else:
                idx=int(item.get('index',-1))
                if idx<0 or idx>=len(sources):raise ValueError('Arquivo ausente')
                path=sources[idx]
            sec=min(30,max(2,float(item.get('seconds',10))))
            playlist.append((path,sec))
        report(20,"Materiais preparados")
        fit=settings.get('fit','blur')
        if fit=='crop':
            filt=f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=25,format=yuv420p'
        elif fit=='black':
            filt=f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=25,format=yuv420p'
        else:
            filt=f'split=2[bg][fg];[bg]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=20:2[blur];[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[front];[blur][front]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=25,format=yuv420p'
        clips=[]
        remaining=duration;idx=0
        while remaining>0.05 and idx<100:
            path,sec=playlist[idx%len(playlist)]
            sec=min(sec,remaining)
            out=root/f'part_{idx:03}.mp4'
            if path.suffix.lower() in ('.mp4','.webm'):
                run(['-stream_loop','-1','-i',path,'-t',sec,'-an','-vf',filt,'-c:v','libx264','-preset','veryfast','-crf','25',out],timeout=120)
            else:
                run(['-loop','1','-framerate','25','-i',path,'-t',sec,'-vf',filt,'-c:v','libx264','-preset','veryfast','-crf','25',out],timeout=120)
            clips.append(out);remaining-=sec;idx+=1
            report(20+int(55*min(1,(duration-remaining)/duration)),f"Preparando cenas: {idx} prontas")
        concat=root/'concat.txt'
        concat.write_text(''.join("file '"+str(f).replace('\\','/')+"'\n" for f in clips),encoding='utf-8')
        ass=root/'captions.ass'
        text=make_ass(segments).replace('PlayResX: 720',f'PlayResX: {w}').replace('PlayResY: 900',f'PlayResY: {h}')
        fitted=[]
        for event in text.splitlines():
            if event.startswith('Dialogue: '):
                parts=event.split(',',9)
                if len(parts)==10:
                    size=32 if parts[3]=='English' else 26
                    wrapped,new_size=_wrap_caption(parts[9],int(w*.78),size)
                    parts[9]=r'{\fs'+str(new_size)+'}'+wrapped
                    event=','.join(parts)
            fitted.append(event)
        ass.write_text('\n'.join(fitted)+'\n',encoding='utf-8-sig')
        report(77,"Preparando audio e legendas")
        audio=None
        if settings.get('youtube_url'):
            audio=fetch_audio_for_playback(settings['youtube_url'],cache)
        else:
            parts_audio=fields.get('audio',[])
            if not parts_audio:raise ValueError('Audio nao encontrado')
            ext=Path(parts_audio[0].get_filename() or '').suffix.lower()
            if ext not in ('.mp3','.wav','.m4a','.mp4','.flac','.ogg'):raise ValueError('Formato de audio invalido')
            audio=root/('audio'+ext);audio.write_bytes(parts_audio[0].get_payload(decode=True))
        out=cache/('musicsense_custom_'+uuid.uuid4().hex[:12]+'.mp4')
        report(80,"Aplicando legendas e finalizando MP4")
        cmd=[str(FF),'-hide_banner','-loglevel','error','-y','-progress','pipe:1','-nostats','-f','concat','-safe','0','-i',str(concat),'-i',str(audio),'-t',str(duration),'-vf','subtitles=captions.ass','-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','24','-c:a','aac','-b:a','160k','-movflags','+faststart',str(out)]
        with subprocess.Popen(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) as proc:
            for line in proc.stdout:
                if line.startswith('out_time_ms='):
                    try:report(min(99,80+int(19*int(line.split('=',1)[1])/1000000/duration)),"Renderizando video e legendas")
                    except (ValueError,ZeroDivisionError):pass
            err=proc.stderr.read()
            if proc.wait()!=0:raise RuntimeError('Falha no FFmpeg: '+err[-500:])
        report(100,"Video pronto")

        return '/cache/'+out.name
