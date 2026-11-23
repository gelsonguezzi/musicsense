"""Metrica publica de visualizacoes, obtida video a video quando disponivel."""
import json
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

YTDLP=Path(r"C:\Yt-dlp\yt-dlp.exe")
ID=re.compile(r"^[A-Za-z0-9_-]{11}$")
LOCK=threading.RLock()
CACHE_NAME="youtube_views_227.json"
CACHE_AGE=24*60*60


def counts(ids, cache, progress=None):
    if not isinstance(ids,list) or len(ids)>40 or not ids or any(
        not isinstance(v,str) or not ID.fullmatch(v) for v in ids):
        raise ValueError("Lista de IDs invalida (maximo 40)")
    ids=list(dict.fromkeys(ids))
    dest=cache/CACHE_NAME
    with LOCK:
        try:data=json.loads(dest.read_text(encoding="utf-8"))
        except (OSError,ValueError):data={}
    now=time.time()
    fresh={vid:record.get("views") for vid in ids
           if isinstance((record:=data.get(vid)),dict)
           and now-float(record.get("at",0))<CACHE_AGE}
    remaining=[vid for vid in ids if vid not in fresh]
    result=dict(fresh)
    def resolve(vid):
        command=[str(YTDLP),"--ignore-config","--no-warnings",
                 "--skip-download","--no-playlist","--socket-timeout","7",
                 "--retries","1","--print","%(view_count)s",
                 "https://www.youtube.com/watch?v="+vid]
        try:
            p=subprocess.run(command,capture_output=True,text=True,timeout=27)
            raw=p.stdout.strip().splitlines()
            value=raw[-1] if raw else ""
            return int(value) if p.returncode==0 and value.isdigit() else None
        except Exception:
            return None
    count=len(ids)
    if progress:progress(int(98*len(fresh)/count),"Visualizacoes conhecidas: "+str(len(fresh))+"/"+str(count))
    if remaining:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures={pool.submit(resolve,vid):vid for vid in remaining}
            for fut in as_completed(futures):
                vid=futures[fut]
                try:views=fut.result()
                except Exception:views=None
                result[vid]=views
                if progress:progress(int(98*len(result)/count),
                   "Consultando visualizacoes: "+str(len(result))+"/"+str(count))
    with LOCK:
        try:latest=json.loads(dest.read_text(encoding="utf-8"))
        except (OSError,ValueError):latest={}
        for vid,views in result.items():
            latest[vid]={"views":views,"at":time.time()}
        dest.write_text(json.dumps(latest,ensure_ascii=False),encoding="utf-8")
    return {key:val for key,val in result.items() if isinstance(val,int) and val>=0}
