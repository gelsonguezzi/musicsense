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
        import argostranslate.package as pkg
        langs=tr.get_installed_languages()
        origin=next((x for x in langs if x.code==source),None)
        target=next((x for x in langs if x.code=='pt'),None)
        if origin and target:
            translator=origin.get_translation(target)
            return [translator.translate(line) for line in lines], 'argos-local'
    except Exception: pass
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
            _MODEL=WhisperModel(os.getenv('MUSICSENSE_MODEL','small'),device='cpu',compute_type='int8',cpu_threads=min(6,os.cpu_count() or 4),num_workers=1,local_files_only=True)
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
        segments,info=model.transcribe(str(filepath),language=language or None,word_timestamps=True,vad_filter=False,beam_size=4,best_of=3,condition_on_previous_text=True,initial_prompt='English song lyrics, sung words and spoken introductions.',no_speech_threshold=0.85)
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
    groups=[g for g in groups if g[2].strip()]
    texts=[g[2] for g in groups]
    translations,engine=translate_lines(texts,info.language)
    output=[{'start':a,'end':b,'original':txt,'translation':translations[i], 'words':ws} for i,(a,b,txt,ws) in enumerate(groups)]
    return {'language':info.language,'translation_engine':engine,'segments':output,'audio_duration':round(info.duration or 0,2)}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT),**kw)
    def do_GET(self):
        if urlparse(self.path).path=='/api/health': return self.send_json({'ok':True,'mode':'local'})
        return super().do_GET()
    def send_json(self,obj,status=200):
        data=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_POST(self):
        route=urlparse(self.path).path
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

