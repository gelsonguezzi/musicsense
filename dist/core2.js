const $=id=>document.getElementById(id);
let analyzed=null,lastFile=null,sourceMode='none',currentVideoId=null,currentTitle='',activeMedia=null;
const demo=[['A música começa aqui','Sua tradução aparece junto com a letra']];
function setStatus(s){$('status').textContent=s}
function draw(){if(analyzed)return;$('original').textContent=demo[0][0];$('translation').textContent=demo[0][1]}
function renderTranslation(seg,time){const el=$('translation'),str=seg.translation||'Tradução indisponível';const pt=str.trim().split(/\s+/).filter(Boolean);const en=(seg.words||[]).filter(w=>Number.isFinite(w.start));if(!pt.length){el.textContent='';return}if(!en.length){el.textContent=str;return}const n=Math.min(pt.length,Math.round(pt.length*en.filter(w=>time>=w.start).length/en.length));el.replaceChildren();pt.forEach((w,i)=>{const s=document.createElement('span');s.className=i<n?'pt-active':'pt-pending';s.textContent=w+(i<pt.length-1?' ':'');el.append(s)})}
function renderSegment(time){if(!analyzed||!Array.isArray(analyzed.segments))return;const segs=analyzed.segments;let seg=segs.find(x=>time>=x.start&&time<x.end+0.35)||null;if(!seg){let next=segs.find(x=>x.start>time);$('original').textContent=next&&next.start-time<1.2?'♪ '+next.original:'';$('translation').textContent='';return}let words=seg.words||[];if(words.length){$('original').replaceChildren();words.forEach(w=>{let s=document.createElement('span');s.textContent=w.text+' ';if(time>=w.start)s.className='active';if($('ball').checked&&time>=w.start&&time<w.end){const dot=document.createElement('span');dot.className='ball';dot.style.animation='none';dot.style.transform='translate(-50%,'+(-5-25*Math.abs(Math.sin((time-w.start)*11)))+'px)';s.prepend(dot)}$('original').append(s)})}else $('original').textContent=seg.original;renderTranslation(seg,time)}
function setMediaMode(mode){sourceMode=mode;const video=$('video'),audio=$('audio');if(mode==='local-video'){video.style.display='block';audio.style.display='none';$('poster').style.display='none'}else if(mode==='local-audio'){video.style.display='none';audio.style.display='block';$('poster').style.display='block'}else if(mode==='youtube'){video.style.display='none';audio.style.display='none';$('poster').style.display='none'}else{video.style.display='none';audio.style.display='none';$('poster').style.display='block'}}
function localTime(){return activeMedia?activeMedia.currentTime:0}
function setProgress(t,duration){if(duration>0)$('progress').value=100*t/duration}
async function checkEngine(){try{let r=await fetch('/api/health');if(!r.ok)throw Error();$('engine').textContent='IA local disponível'}catch{$('engine').textContent='Servidor indisponível'}}
$('file').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;lastFile=f;analyzed=null;currentVideoId=null;currentTitle=f.name;$('filename').textContent=f.name;$('analyze').disabled=false;const video=$('video'),audio=$('audio');video.pause();audio.pause();if(activeMedia&&activeMedia.src?.startsWith('blob:'))URL.revokeObjectURL(activeMedia.src);const url=URL.createObjectURL(f);if(f.type.startsWith('video/')||/\.mp4$/i.test(f.name)){activeMedia=video;video.src=url;setMediaMode('local-video')}else{activeMedia=audio;audio.src=url;setMediaMode('local-audio')}setStatus('Arquivo carregado. Clique em Preparar arquivo com IA.')});
$('analyze').onclick=async()=>{if(!lastFile)return;const b=$('analyze');b.disabled=true;b.textContent='⏳ Processando...';setStatus('Transcrevendo e traduzindo o arquivo. Aguarde...');try{const fd=new FormData();fd.append('file',lastFile);const r=await fetch('/api/analyze',{method:'POST',body:fd});const data=await r.json();if(!r.ok)throw Error(data.error||'Falha na análise');analyzed=data;$('progress').max=100;$('progress').step=.1;renderSegment(0);setStatus('Concluído: '+data.segments.length+' trechos. Tradução: '+data.translation_engine)}catch(e){setStatus('Erro: '+e.message)}finally{b.disabled=false;b.textContent='✦ Preparar arquivo com IA'}};
function syncLocal(){if(!analyzed||!activeMedia)return;renderSegment(localTime());setProgress(localTime(),activeMedia.duration)}
$('audio').addEventListener('timeupdate',syncLocal);$('video').addEventListener('timeupdate',syncLocal);
$('progress').addEventListener('input',()=>{if(activeMedia&&activeMedia.duration>0&&sourceMode!=='youtube')activeMedia.currentTime=activeMedia.duration*Number($('progress').value)/100});
$('ball').addEventListener('change',()=>{if(analyzed)renderSegment(localTime())});
$('captoggle').addEventListener('change',e=>{$('captions').style.display=e.target.checked?'':'none'});
function isTheater(){return $('viewer').classList.contains('ipad-theater')}
function setTheater(on){$('viewer').classList.toggle('ipad-theater',on);document.body.classList.toggle('ipad-theater-open',on);$('fullscreen').textContent=on?'Sair da tela ampliada':'Tela cheia'}
async function fullScreen(){
  if(isTheater()){setTheater(false);return}
  if(document.fullscreenElement){try{await document.exitFullscreen()}catch{}return}
  const viewer=$('viewer');
  if(viewer.requestFullscreen){
    try{await viewer.requestFullscreen();return}catch(e){}
  }
  setTheater(true);
}
document.addEventListener('fullscreenchange',()=>{$('fullscreen').textContent=document.fullscreenElement?'Sair da tela cheia':'Tela cheia'});
let lastTouchTap=0;
$('viewer').addEventListener('touchend',e=>{
  if(e.changedTouches.length!==1||e.target.closest('button,input,video,a'))return;
  const now=Date.now();
  if(now-lastTouchTap<340){e.preventDefault();lastTouchTap=0;fullScreen()}else lastTouchTap=now;
},{passive:false});$('fullscreen').onclick=fullScreen;$('viewer').addEventListener('dblclick',fullScreen);
$('next').addEventListener('click',()=>{if(!analyzed||!activeMedia||sourceMode==='youtube')return;const next=analyzed.segments.find(x=>x.start>localTime()+.15);if(next)activeMedia.currentTime=next.start});
$('repeatLine').onclick=()=>{if(!analyzed||!activeMedia)return setStatus('Analise uma música primeiro.');const seg=analyzed.segments.filter(x=>x.start<=localTime()).at(-1);if(seg)activeMedia.currentTime=seg.start};
draw();checkEngine();