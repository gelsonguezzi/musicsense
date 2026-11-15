"""Local vocal separation. No paid APIs."""
from pathlib import Path
import subprocess,tempfile,uuid
from youtube_support import fetch_audio_for_playback
PY=Path(__file__).parent/'.venv_demucs'/'Scripts'/'python.exe'
def separate(url,cache,progress=None):
 def report(n,s):
  if progress:progress(n,s)
 if not PY.exists():raise RuntimeError('Motor de separacao vocal ainda nao instalado')
 report(5,'Preparando audio da musica')
 audio=fetch_audio_for_playback(url,cache)
 with tempfile.TemporaryDirectory(prefix='musicsense_stems_') as tmp:
  report(15,'Separando voz e instrumentos com IA local. Pode levar alguns minutos')
  cmd=[str(PY),str(Path(__file__).parent/'demucs_compat_214.py'),'--two-stems=vocals','-n','htdemucs','-o',tmp,str(audio)]
  try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=1800)
  except subprocess.TimeoutExpired:raise RuntimeError('Separacao excedeu 30 minutos')
  if r.returncode:raise RuntimeError('Demucs: '+r.stderr[-900:])
  base=Path(tmp)/'htdemucs'/audio.stem
  result={}
  for key,filename in [('instrumental','no_vocals.wav'),('vocals','vocals.wav')]:
   src=base/filename
   if not src.is_file():raise RuntimeError('Faixa '+filename+' nao foi produzida')
   dest=cache/('musicsense_'+key+'_'+uuid.uuid4().hex[:10]+'.mp3')
   cmd=[r'C:\Yt-dlp\ffmpeg.exe','-hide_banner','-loglevel','error','-y','-i',str(src),'-codec:a','libmp3lame','-q:a','3',str(dest)]
   subprocess.run(cmd,check=True,capture_output=True,timeout=180)
   result[key]='/cache/'+dest.name
  report(100,'Separacao concluida')
  return result
