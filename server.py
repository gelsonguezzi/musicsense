import json, os, sys, tempfile, traceback, re, threading, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from email.parser import BytesParser
from email.policy import default

ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'cache'; CACHE.mkdir(exist_ok=True)

def translate_lines(lines, source):
    try:
        import argostranslate.translate as tr
        langs={x.code:x for x in tr.get_installed_languages()}
        if source=='pt':return list(lines),'original-portugues'
        if source in langs and 'pt' in langs:
            # Direct translation first; fall back to Italian -> English -> Portuguese.
            if source=='it' and 'en' in langs:
                via=langs['it'].get_translation(langs['en'])
                target=langs['en'].get_translation(langs['pt'])
                return [target.translate(via.translate(line)) if line.strip() else '' for line in lines], 'argos-it-en-pt'
            translator=langs[source].get_translation(langs['pt'])
            return [translator.translate(line) if line.strip() else '' for line in lines], 'argos-local'
    except Exception as exc:
        print('[TRANSLATION ERROR]',repr(exc),flush=True)
    return ['' for _ in lines], 'indisponivel'

_MODEL = None
_MODEL_LOCK = threading.Lock()
_ANALYZE_LOCK = threading.Lock()

def get_model():
    global _MODEL
    with _MODEL_LOCK:
        if _MODEL is None:
            from faster_whisper import WhisperModel
            start=time.monotonic()
            print('[IA] Carregando modelo...',flush=True)
            _MODEL=WhisperModel(os.getenv('MUSICSENSE_MODEL','small'),device='cpu',compute_type='int8',cpu_threads=min(6,os.cpu_count() or 4),num_workers=1,local_files_only=False)
            print('[IA] Modelo pronto em %.1fs'%(time.monotonic()-start),flush=True)
    return _MODEL

def analyze(filepath, language):
    # Compatibilidade com PyAV 19: faster-whisper passa metadata_errors,
    # argumento que esta versao do PyAV nao aceita.
    import av
    if not getattr(av.open, '_musicsense_compat', False):
        original_open = av.open
        def compatible_open(*args, **kwargs):
            kwargs.pop('metadata_errors', None)
            return original_open(*args, **kwargs)
        compatible_open._musicsense_compat = True
        av.open = compatible_open
    with _ANALYZE_LOCK:
        start=time.monotonic()
        model=get_model()
        segments,info=model.transcribe(str(filepath),language=language or None,word_timestamps=True,vad_filter=False,beam_size=4,best_of=3,condition_on_previous_text=False,initial_prompt=None,no_speech_threshold=0.65,compression_ratio_threshold=2.2)
        segments=list(segments)
        print('[IA] Transcricao em %.1fs'%(time.monotonic()-start),flush=True)
    # Frases de karaoke: usar os tempos REAIS das palavras, nunca frases enormes.
    # O VAD desativado preserva a voz cantada que antes era descartada.
    groups=[]
    for s in segments:
        words=[{'text':w.word.strip(),'start':round(w.start if w.start is not None else s.start,3),'end':round(w.end if w.end is not None else s.end,3)} for w in (s.words or []) if w.word.strip()]
        if not words:
            if s.text.strip():groups.append((round(s.start,3),round(s.end,3),s.text.strip(),[]))
            continue
        chunk=[]
        for w in words:
            if chunk and (w['start']-chunk[-1]['end']>0.8 or w['end']-chunk[0]['start']>5.5 or len(chunk)>=9):
                groups.append((chunk[0]['start'],chunk[-1]['end'],' '.join(x['text'] for x in chunk),chunk))
                chunk=[]
            chunk.append(w)
            if w['text'].endswith(('.', '?', '!', ';', ':')) and len(chunk)>=3:
                groups.append((chunk[0]['start'],chunk[-1]['end'],' '.join(x['text'] for x in chunk),chunk))
                chunk=[]
        if chunk:groups.append((chunk[0]['start'],chunk[-1]['end'],' '.join(x['text'] for x in chunk),chunk))
    # Reject recurring Whisper hallucinations and invalid word timestamps.
    groups=[g for g in groups if g[2].strip() and g[1]>g[0] and
        not re.search(r'English song lyrics, sung words and spoken introductions',g[2],re.I)]
    groups.sort(key=lambda g:g[0])
    cleaned=[]
    for g in groups:
        if cleaned and g[0]<cleaned[-1][1]-0.3:
            if g[1]<=cleaned[-1][1]:continue
            g=(cleaned[-1][1],g[1],g[2],[w for w in g[3] if w['end']>cleaned[-1][1]])
        if g[1]>g[0]:cleaned.append(g)
    groups=cleaned
    texts=[g[2] for g in groups]
    translations,engine=translate_lines(texts,info.language)
    output=[{'start':a,'end':b,'original':txt,'translation':translations[i], 'words':ws} for i,(a,b,txt,ws) in enumerate(groups)]
    return {'language':info.language,'translation_engine':engine,'segments':output,'audio_duration':round(info.duration or 0,2)}

_EXPORT_JOBS={}
_EXPORT_LOCK=__import__('threading').Lock()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT),**kw)
    def search_youtube(self,query):
        import subprocess
        cmd=[str(Path(r'C:\Yt-dlp\yt-dlp.exe') if Path(r'C:\Yt-dlp\yt-dlp.exe').is_file() else (__import__('shutil').which('yt-dlp') or 'yt-dlp')),'--ignore-config','--flat-playlist','--dump-single-json','--no-warnings','--skip-download','ytsearch15:'+query]
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=35)
        if r.returncode:raise RuntimeError((r.stderr or 'Busca indisponível')[-250:])
        data=json.loads(r.stdout)
        videos=[]
        for item in data.get('entries',[]):
            if not item:continue
            vid=item.get('id','')
            if not re.fullmatch('[A-Za-z0-9_-]{11}',vid):continue
            videos.append({'id':vid,'title':item.get('title') or 'Vídeo do YouTube','channel':item.get('channel') or item.get('uploader') or '', 'duration':item.get('duration')})
        return videos

    def do_GET(self):
        if urlparse(self.path).path=='/api/export-progress':
            from urllib.parse import parse_qs
            job=parse_qs(urlparse(self.path).query).get('id',[''])[0]
            with _EXPORT_LOCK: data=_EXPORT_JOBS.get(job)
            if not data:return self.send_json({'error':'Processo nao encontrado'},404)
            return self.send_json(dict(data))
        if urlparse(self.path).path=='/api/health': return self.send_json({'ok':True,'mode':'local'})
        if urlparse(self.path).path=='/api/youtube-search':
            from urllib.parse import parse_qs
            query=parse_qs(urlparse(self.path).query).get('q',[''])[0].strip()
            if not 2<=len(query)<=100:return self.send_json({'error':'Informe um artista ou música (2 a 100 caracteres).'},400)
            try:return self.send_json({'videos':self.search_youtube(query)})
            except Exception as exc:return self.send_json({'error':'Busca indisponível: '+str(exc)},502)

        return super().do_GET()
    def send_json(self,obj,status=200):
        data=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_POST(self):
        route=urlparse(self.path).path
        if route in ('/api/download-original','/api/separate-six'):
            try:
                import uuid,threading
                from youtube_support import video_id_from_url
                size=int(self.headers.get('Content-Length','0'))
                if size<1 or size>4096:return self.send_json({'error':'Link invalido'},400)
                data=json.loads(self.rfile.read(size).decode('utf-8'))
                url=str(data.get('url',''))
                video_id_from_url(url)
                job=uuid.uuid4().hex
                with _EXPORT_LOCK:_EXPORT_JOBS[job]={'percent':1,'stage':'Iniciando','done':False}
                def work():
                    def update(pct,stage):
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(percent=pct,stage=stage)
                    try:
                        from features_218 import download_original,separate_six
                        if route=='/api/download-original':
                            output=download_original(url,CACHE,update)
                            result={'video_url':output}
                        else:result=separate_six(url,CACHE,update)
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(done=True,percent=100,stage='Concluido',**result)
                    except Exception as exc:
                        traceback.print_exc()
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(done=True,error=str(exc),stage='Falha')
                threading.Thread(target=work,daemon=True).start()
                return self.send_json({'job_id':job})
            except Exception as exc:return self.send_json({'error':str(exc)},400)
        if route=='/api/export-stem-karaoke':
            try:
                import uuid,threading
                size=int(self.headers.get('Content-Length','0'))
                if size<1 or size>240000:return self.send_json({'error':'Dados excedem limite'},413)
                data=json.loads(self.rfile.read(size).decode('utf-8'))
                job=uuid.uuid4().hex
                with _EXPORT_LOCK:_EXPORT_JOBS[job]={'percent':1,'stage':'Preparando exportacao','done':False}
                def work():
                    def update(pct,stage):
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(percent=pct,stage=stage)
                    try:
                        from stem_karaoke_215 import export
                        output=export(data.get('stem'),data.get('mode'),data.get('segments'),CACHE,progress=update)
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(done=True,percent=100,stage='Concluido',video_url=output)
                    except Exception as exc:
                        traceback.print_exc()
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(done=True,error=str(exc),stage='Erro na exportacao')
                threading.Thread(target=work,daemon=True).start()
                return self.send_json({'job_id':job})
            except Exception as exc:return self.send_json({'error':str(exc)},400)
        if route=='/api/separate-vocals':
            try:
                import uuid,threading
                size=int(self.headers.get('Content-Length','0'))
                if size<1 or size>4096:return self.send_json({'error':'Link invalido'},400)
                data=json.loads(self.rfile.read(size).decode('utf-8'))
                from youtube_support import video_id_from_url
                video_id_from_url(str(data.get('url','')))
                job=uuid.uuid4().hex
                with _EXPORT_LOCK:_EXPORT_JOBS[job]={'percent':1,'stage':'Iniciando separacao vocal','done':False}
                def work():
                    def update(pct,stage):
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(percent=pct,stage=stage)
                    try:
                        from vocal_212 import separate
                        result=separate(data['url'],CACHE,progress=update)
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(done=True,percent=100,stage='Concluido',**result)
                    except Exception as exc:
                        traceback.print_exc()
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(done=True,error=str(exc),stage='Falha na separacao')
                threading.Thread(target=work,daemon=True).start()
                return self.send_json({'job_id':job})
            except Exception as exc:return self.send_json({'error':str(exc)},400)
        if route=='/api/export-custom-start':
            try:
                import uuid,threading
                size=int(self.headers.get('Content-Length','0'))
                if size<1 or size>180*1024*1024:return self.send_json({'error':'Materiais excedem 180 MB'},413)
                ct=self.headers.get('Content-Type','')
                if not ct.startswith('multipart/form-data'):return self.send_json({'error':'Formulario invalido'},400)
                body=self.rfile.read(size);job=uuid.uuid4().hex
                with _EXPORT_LOCK:_EXPORT_JOBS[job]={'percent':3,'stage':'Arquivos recebidos','done':False}
                def work():
                    def update(pct,stage):
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(percent=pct,stage=stage)
                    try:
                        from clip_export_210 import export
                        result=export(ct,body,CACHE,progress=update)
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(done=True,video_url=result,percent=100,stage='Concluido')
                    except Exception as exc:
                        traceback.print_exc()
                        with _EXPORT_LOCK:_EXPORT_JOBS[job].update(done=True,error=str(exc),stage='Erro na exportacao')
                threading.Thread(target=work,daemon=True).start()
                return self.send_json({'job_id':job})
            except Exception as exc:return self.send_json({'error':str(exc)},500)
        if route=='/api/export-custom-clip':
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<1 or size>180*1024*1024:return self.send_json({'error':'Materiais excedem 180 MB'},413)
                ct=self.headers.get('Content-Type','')
                if not ct.startswith('multipart/form-data'):return self.send_json({'error':'Envie formulario de arquivos'},400)
                from clip_export_210 import export
                result=export(ct,self.rfile.read(size),CACHE)
                return self.send_json({'video_url':result})
            except ValueError as exc:return self.send_json({'error':str(exc)},400)
            except Exception as exc:
                traceback.print_exc()
                return self.send_json({'error':str(exc)},502)
        if route=='/api/export-youtube-original':
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<1 or size>200000:return self.send_json({'error':'Dados invalidos'},400)
                payload=json.loads(self.rfile.read(size).decode('utf-8'))
                from export_video_208 import export_youtube_video
                result=export_youtube_video(str(payload.get('url','')),payload.get('segments'),CACHE)
                return self.send_json({'video_url':result,'source':'youtube-video'})
            except ValueError as exc:return self.send_json({'error':str(exc)},400)
            except Exception as exc:
                traceback.print_exc()
                return self.send_json({'error':str(exc)},502)
        if route=='/api/export-youtube-video':
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<1 or size>200000:return self.send_json({'error':'Dados invalidos'},400)
                payload=json.loads(self.rfile.read(size).decode('utf-8'))
                from youtube_support import fetch_audio_for_playback, video_id_from_url
                from studio_export import export_multipart
                url=str(payload.get('url',''))
                video_id=video_id_from_url(url)
                segments=payload.get('segments')
                if not isinstance(segments,list) or not 1<=len(segments)<=500:
                    return self.send_json({'error':'Legendas invalidas'},400)
                audio=fetch_audio_for_playback(url,CACHE)
                if audio.stat().st_size>100*1024*1024:
                    return self.send_json({'error':'Audio excede 100 MB'},413)
                import uuid
                boundary='musicexport'+uuid.uuid4().hex
                def field(name,blob,filename=None):
                    header=('--'+boundary+'\\r\\nContent-Disposition: form-data; name="'+name+'"'+('; filename="'+filename+'"' if filename else '')+'\\r\\nContent-Type: application/octet-stream\\r\\n\\r\\n')
                    return header.replace('\\r','\r').replace('\\n','\n').encode()+blob+b'\r\n'
                body=field('file',audio.read_bytes(),audio.name)+field('segments',json.dumps(segments,ensure_ascii=False).encode('utf-8'))+('--'+boundary+'--\r\n').encode()
                result=export_multipart('multipart/form-data; boundary='+boundary,body,CACHE)
                return self.send_json({'video_url':result,'source':'youtube-audio','video_id':video_id})
            except ValueError as exc:return self.send_json({'error':str(exc)},400)
            except Exception as exc:
                traceback.print_exc()
                return self.send_json({'error':str(exc)},502)
        if route=='/api/export-video':
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<1 or size>101*1024*1024:return self.send_json({'error':'Arquivo muito grande'},413)
                from studio_export import export_multipart
                result=export_multipart(self.headers.get('Content-Type',''),self.rfile.read(size),CACHE)
                return self.send_json({'video_url':result})
            except ValueError as exc:return self.send_json({'error':str(exc)},400)
            except Exception as exc:
                traceback.print_exc()
                return self.send_json({'error':str(exc)},500)
        if route=='/api/youtube-playback':
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<1 or size>4096:return self.send_json({'error':'Link invÃ¡lido'},400)
                payload=json.loads(self.rfile.read(size).decode('utf-8'))
                from youtube_support import fetch_audio_for_playback, video_id_from_url
                url=str(payload.get('url',''))
                path=fetch_audio_for_playback(url,CACHE)
                return self.send_json({'audio_url':'/cache/'+path.name,'video_id':video_id_from_url(url)})
            except ValueError as exc:return self.send_json({'error':str(exc)},400)
            except Exception as exc:
                traceback.print_exc()
                return self.send_json({'error':str(exc)},502)
        if route=='/api/youtube':
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<1 or size>4096:return self.send_json({'error':'Link invÃ¡lido'},400)
                payload=json.loads(self.rfile.read(size).decode('utf-8'))
                from youtube_support import fetch_audio_and_analyze
                result=fetch_audio_and_analyze(str(payload.get('url','')),CACHE,analyze)
                return self.send_json(result)
            except ValueError as exc:return self.send_json({'error':str(exc)},400)
            except Exception as exc:
                traceback.print_exc()
                return self.send_json({'error':str(exc)},502)
        if route!='/api/analyze':return self.send_json({'error':'Rota inexistente'},404)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>100*1024*1024:return self.send_json({'error':'Arquivo deve ter atÃ© 100 MB'},413)
            content_type=self.headers.get('Content-Type','')
            if not content_type.lower().startswith('multipart/form-data'):
                return self.send_json({'error':'Envie o arquivo como multipart/form-data'},400)
            payload=self.rfile.read(length)
            mime=(f'MIME-Version: 1.0\r\nContent-Type: {content_type}\r\n\r\n'.encode('utf-8')+payload)
            form=BytesParser(policy=default).parsebytes(mime)
            if not form.is_multipart():
                return self.send_json({'error':'FormulÃ¡rio de upload invÃ¡lido'},400)
            field=next((part for part in form.iter_parts() if part.get_param('name',header='content-disposition')=='file'),None)
            if field is None or not field.get_filename():
                return self.send_json({'error':'Selecione um arquivo MP3, WAV ou M4A'},400)
            name=str(field.get_filename()); ext=Path(name).suffix.lower()
            if ext not in ('.mp3','.wav','.m4a','.flac','.ogg','.mp4','.wma'):return self.send_json({'error':'Formato nÃ£o suportado'},400)
            import hashlib
            blob=field.get_payload(decode=True) or b''
            if len(blob)>100*1024*1024:return self.send_json({'error':'Arquivo muito grande'},413)
            key=hashlib.sha256(blob).hexdigest(); cached=CACHE/(key+'.json')
            if cached.exists():return self.send_json(json.loads(cached.read_text(encoding='utf-8')))
            with tempfile.NamedTemporaryFile(suffix=ext,delete=False) as tmp:tmp.write(blob);tmp_path=tmp.name
            try: result=analyze(tmp_path,'en')
            finally: os.unlink(tmp_path)
            cached.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
            return self.send_json(result)
        except Exception as e:
            traceback.print_exc();return self.send_json({'error':str(e),'hint':'Confira a instalaÃ§Ã£o de faster-whisper e FFmpeg.'},500)

if __name__=='__main__':
    print('MusicSense AI: http://localhost:8765')
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()


