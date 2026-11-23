/* MusicSense 226 - Mesa detalhada dinamica e sincronizada. */
(function(){
'use strict';
const get=id=>document.getElementById(id);
const btn=get('separateSix');
if(!btn)return;
// Modo unico e rapido: sem opcao de bateria detalhada.
const order=['lead_vocals','vocals','backing_vocals','kick','snare','cymbals','toms','drums','bass','guitar','piano','other'];
let keys=[];
const labels={lead_vocals:'Voz principal',vocals:'Voz',backing_vocals:'Apoios vocais',kick:'Bumbo',snare:'Caixa',cymbals:'Pratos',toms:'Tons',drums:'Bateria',bass:'Baixo',guitar:'Guitarra',piano:'Piano',other:'Outros'};
const label=key=>labels[key]||key.replaceAll('_',' ');
const getKeys=tracks=>order.filter(k=>tracks[k]).slice(0,10);
const nap=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const format=s=>String(Math.floor(s/60)).padStart(2,'0')+':'+String(Math.floor(s%60)).padStart(2,'0');
const message=s=>{if(typeof setStatus==='function')setStatus(s)};
const dl=(href,name)=>{const a=document.createElement('a');a.href=href;a.download=name;document.body.append(a);a.click();a.remove()};
function meter(label){
 const wrap=document.createElement('div');wrap.className='ms224-progress';wrap.setAttribute('role','status');wrap.setAttribute('aria-live','polite');
 const text=document.createElement('div');text.className='ms224-progress-label';const bar=document.createElement('progress');bar.max=100;bar.value=0;const pct=document.createElement('strong');
 wrap.append(text,bar,pct);
 const update=(value,stage)=>{
   const n=Math.max(0,Math.min(100,Math.floor(Number(value)||0)));
   bar.value=n;pct.textContent=n+'%';text.textContent=stage||label;
   message(label+' • '+n+'% • '+(stage||'Processando'));
 };
 update(0,'Iniciando');
 return {wrap,update};
}
async function task(onProgress,detailed=false){
 const song=(typeof currentVideoId!=='undefined'&&currentVideoId)||(typeof ytId!=='undefined'&&ytId);
 if(!song)throw Error('Escolha primeiro um link do YouTube.');
 const r=await fetch(detailed?'/api/separate-detailed':'/api/separate-six',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:'https://www.youtube.com/watch?v='+song})});
 const data=await r.json();if(!r.ok)throw Error(data.error||'Falha ao iniciar a separacao');
 for(let i=0;i<3600;i++){
  await nap(1000);
  const progress=await fetch('/api/export-progress?id='+encodeURIComponent(data.job_id),{cache:'no-store'});
  const j=await progress.json();
  if(!progress.ok)throw Error(j.error||'Erro ao consultar processamento');
  onProgress(Math.min(65,Math.floor((Number(j.percent)||0)*.65)),j.stage);
  if(j.done){if(j.error)throw Error(j.error);return {tracks:j.tracks||{},note:j.note||'',quality:j.quality||''}}
 }
 throw Error('Tempo limite da separacao excedido.');
}
async function prepareAudio(tracks,progress){
 const AudioContext=window.AudioContext||window.webkitAudioContext;
 if(!AudioContext)throw Error('Este navegador nao possui suporte a mixagem de audio.');
 const context=new AudioContext();
 const buffers={};
 keys=getKeys(tracks);
 try{
  const present=keys.filter(k=>tracks[k]);
  for(let i=0;i<present.length;i++){
   const key=present[i];
   progress(65+Math.floor(i*35/present.length), 'Carregando '+label(key));
   const response=await fetch(tracks[key],{cache:'default'});
   if(!response.ok)throw Error('Falha ao carregar '+label(key));
   const raw=await response.arrayBuffer();
   // Decodificacao completa permite ligar/desligar no mesmo instante.
   const decoded=await context.decodeAudioData(raw);
   buffers[key]=decoded;
   progress(65+Math.floor((i+1)*35/present.length),'Trilha pronta: '+label(key));
  }
  return {context,buffers};
 }catch(e){await context.close().catch(()=>{});throw e;}
}
function openMixer(context,buffers,tracks,note){
 const available=keys.filter(k=>buffers[k]);
 if(!available.length)throw Error('Nenhum instrumento disponivel.');
 const dialog=document.createElement('dialog');dialog.className='modal ms-mixer ms224 ms226';
 const title=document.createElement('h2');title.textContent='Mesa de instrumentos • '+available.length+' trilhas';
 const help=document.createElement('p');help.textContent='Toque no nome do instrumento para adicionar ou retirar da musica. As trilhas sao estimativas da IA.';
 const hint=document.createElement('p');hint.className='ms224-hint';hint.textContent='M = silenciar  •  S = ouvir apenas esta trilha. Os componentes extras sao estimativas independentes de IA.';
 const noteEl=document.createElement('p');noteEl.className='ms226-note';noteEl.textContent=note||'Qualidade de piano pode variar com a gravacao.';
 dialog.append(title,help,hint,noteEl);
 const controls=document.createElement('div');controls.className='mixer-controls';
 const play=document.createElement('button');play.className='btn primary';play.textContent='▶ Reproduzir';
 const stop=document.createElement('button');stop.className='btn ghost';stop.textContent='■ Parar';
 const close=document.createElement('button');close.className='btn ghost';close.textContent='Fechar';
 controls.append(play,stop,close);dialog.append(controls);
 const seek=document.createElement('input');seek.type='range';seek.min=0;seek.max=100;seek.step=.1;seek.value=0;seek.style.width='100%';seek.setAttribute('aria-label','Posicao da musica');dialog.append(seek);
 const clock=document.createElement('p');clock.className='ms224-clock';clock.textContent='00:00';
 dialog.append(clock);
 const area=document.createElement('div');area.className='mixer-tracks';dialog.append(area);
 const gains={},rows={},inputs={};
 function addTrack(key, initiallyOn=false){
  if(!available.includes(key))available.push(key);
  const row=document.createElement('div');row.className='mixer-row ms224-row';
  const toggle=document.createElement('button');toggle.className='ms224-toggle';toggle.type='button';toggle.textContent=label(key);
  const mute=document.createElement('button');mute.type='button';mute.className='btn ghost small';mute.textContent='M';mute.title='Silenciar';
  const solo=document.createElement('button');solo.type='button';solo.className='btn ghost small';solo.textContent='S';solo.title='Isolar este instrumento na reproducao e marcar para exportar';
  const volume=document.createElement('input');volume.type='range';volume.min=0;volume.max=100;volume.value=80;volume.setAttribute('aria-label','Volume de '+label(key));
  const download=document.createElement('button');download.type='button';download.className='btn ghost small';download.textContent='⬇ MP3';
  download.onclick=()=>dl(tracks[key],'MusicSense_'+key+'.mp3');
  const gain=context.createGain();gain.gain.value=0;gain.connect(context.destination);gains[key]=gain;
  inputs[key]={on:initiallyOn,mute:false,solo:false,volume,toggle,muteButton:mute,soloButton:solo};
  toggle.onclick=()=>{const enabled=!inputs[key].on;available.forEach(k=>inputs[k].solo=false);inputs[key].on=enabled;inputs[key].mute=false;update()};
  mute.onclick=()=>{inputs[key].mute=!inputs[key].mute;if(inputs[key].mute)inputs[key].solo=false;update()};
  solo.onclick=()=>{inputs[key].solo=!inputs[key].solo;if(inputs[key].solo){inputs[key].on=true;inputs[key].mute=false;}update()};
  volume.oninput=update;
  row.append(toggle,mute,solo,volume,download);area.append(row);rows[key]=row;
  for(const name of [...available].sort((a,b)=>order.indexOf(a)-order.indexOf(b))){
   if(rows[name])area.append(rows[name]);
  }
 }
 for(const key of [...available])addTrack(key,key==='vocals'||key==='lead_vocals');
 const duration=Math.min(...available.map(k=>buffers[k].duration));
 let sources={},playing=false,anchor=context.currentTime,offset=0,raf=0,closed=false,seekMoving=false;
 function elapsed(){
  return playing?Math.min(duration,offset+Math.max(0,context.currentTime-anchor)):offset;
 }
 function update(){
  const solo=available.some(k=>inputs[k].solo);
  available.forEach(k=>{
   const x=inputs[k];
   const enabled=x.on&&!x.mute&&(!solo||x.solo);
   const volume=enabled?Number(x.volume.value)/100:0;
   // Curva curta evita estalos, sem delay perceptivel.
   gains[k].gain.setTargetAtTime(volume,context.currentTime,.012);
   x.toggle.classList.toggle('ms224-on',x.on);
   x.toggle.setAttribute('aria-pressed',String(x.on));
   x.muteButton.classList.toggle('mixer-active',x.mute);
   x.soloButton.classList.toggle('mixer-active',x.solo);
  });
 }
 function kill(){
  Object.values(sources).forEach(s=>{try{s.stop()}catch{}try{s.disconnect()}catch{}});
  sources={};
 }
 function begin(seconds){
  kill();
  offset=Math.max(0,Math.min(Math.max(0,duration-.01),seconds));
  anchor=context.currentTime+.05;
  for(const k of available){
   const src=context.createBufferSource();
   src.buffer=buffers[k];src.connect(gains[k]);src.start(anchor,offset);
   sources[k]=src;
  }
  playing=true;play.textContent='Ⅱ Pausar';
  update();
 }
 function pause(){
  if(!playing)return;
  offset=elapsed();playing=false;kill();play.textContent='▶ Reproduzir';
 }
 play.onclick=async()=>{
  try{
   if(playing){pause();return;}
   await context.resume();
   begin(offset>=duration-.05?0:offset);
  }catch(e){message('Erro ao iniciar instrumentos: '+e.message)}
 };
 stop.onclick=()=>{pause();offset=0;seek.value=0;clock.textContent='00:00'};
 seek.addEventListener('pointerdown',()=>{seekMoving=true});
 seek.addEventListener('pointerup',()=>{seekMoving=false});
 seek.oninput=()=>{const t=duration*Number(seek.value)/100;if(playing)begin(t);else offset=t;clock.textContent=format(t)};
 close.onclick=()=>dialog.close();
 const exporter=window.MusicSenseMixer227?.attach({dialog,controls,context,gains,available,tracks,inputs,duration});
 window.MusicSenseLayout230?.mount({dialog,title,help,hint,noteEl,controls,seek,clock,area});
 async function installVocalParts(two){
  if(!two?.lead_vocals||!two?.backing_vocals||closed)return;
  const added={};
  for(const key of ['lead_vocals','backing_vocals']){
   const r=await fetch(two[key],{cache:'default'});
   if(!r.ok)throw Error('Nao foi possivel carregar '+label(key));
   added[key]=await context.decodeAudioData(await r.arrayBuffer());
  }
  if(closed||!dialog.open)return;
  const prev=inputs.vocals;
  if(!prev)return;
  const wasOn=prev.on&&!prev.mute;
  const wasSolo=prev.solo;
  const oldVolume=prev.volume.value;
  const now=context.currentTime;
  gains.vocals?.gain.setTargetAtTime(0,now,.009);
  try{if(sources.vocals)sources.vocals.stop(now+.06)}catch{}
  delete sources.vocals;
  rows.vocals?.remove();delete rows.vocals;delete inputs.vocals;
  available.splice(available.indexOf('vocals'),1);
  for(const key of ['lead_vocals','backing_vocals']){
   tracks[key]=two[key];buffers[key]=added[key];
   addTrack(key,key==='lead_vocals'?wasOn:true);
  }
  inputs.lead_vocals.volume.value=oldVolume;
  inputs.lead_vocals.solo=wasSolo;
  exporter?.rebindLead?.(gains.lead_vocals);
  if(playing){
   const startAt=Math.max(0,elapsed());
   for(const key of ['lead_vocals','backing_vocals']){
    const source=context.createBufferSource();
    source.buffer=buffers[key];source.connect(gains[key]);
    source.start(now+.045,Math.min(startAt,Math.max(0,buffers[key].duration-.1)));
    sources[key]=source;
   }
  }
  title.textContent='Mesa de instrumentos • '+available.length+' trilhas';
  noteEl.textContent='Voz principal e apoios vocais estimados por IA. Desligue Voz principal e mantenha Apoios vocais no karaokê.';
  update();
 }
 function tick(){
  if(closed)return;
  const t=elapsed();
  if(playing&&t>=duration-.05){pause();offset=duration;}
  if(!seekMoving)seek.value=String(duration?100*t/duration:0);
  clock.textContent=format(t);
  raf=requestAnimationFrame(tick);
 }
 dialog.addEventListener('close',async()=>{closed=true;cancelAnimationFrame(raf);pause();Object.values(gains).forEach(g=>g.disconnect());await context.close().catch(()=>{});dialog.remove()},{once:true});
 try{document.getElementById('audio')?.pause();document.getElementById('video')?.pause();if(typeof ytPlayer!=='undefined'&&ytPlayer?.pauseVideo)ytPlayer.pauseVideo()}catch{};
 document.body.append(dialog);dialog.showModal();
 const song=(typeof currentVideoId!=='undefined'&&currentVideoId)||(typeof ytId!=='undefined'&&ytId);
 if(song)window.MusicSenseVocal229?.start({dialog,url:'https://www.youtube.com/watch?v='+song,onReady:installVocalParts});
 update();tick();
 message('Mesa pronta com '+available.length+' trilhas. Toque no instrumento para combina-lo com a voz.');
}
btn.onclick=async()=>{
 const original=btn.innerHTML;
 btn.disabled=true;
 const progress=meter('Mesa de instrumentos');
 const prior=btn.nextElementSibling;
 btn.insertAdjacentElement('afterend',progress.wrap);
 const update=(percent,stage)=>{
  progress.update(percent,stage);
  btn.innerHTML='<span class="actionicon">⏳</span><span><strong>'+Math.floor(Number(percent)||0)+'% concluido</strong><small>Separando e preparando instrumentos</small></span>';
 };
 let ctx=null;
 try{
  const result=await task((p,s)=>update(p,s),false);
  const tracks=result.tracks;
  // O backend ja atingiu 100%, agora inicia uma etapa distinta com percentuais reais.
  update(65,'Carregando '+Object.keys(tracks).length+' trilhas sincronizadas');
  const prepared=await prepareAudio(tracks,update);
  ctx=prepared.context;
  update(100,'Trilhas carregadas');
  openMixer(ctx,prepared.buffers,tracks,result.note||'Separação rápida concluída. Voz principal e apoios serão preparados na mesa em segundo plano.');ctx=null;
 }catch(e){if(ctx)ctx.close().catch(()=>{});message('Falha na Mesa de Instrumentos: '+e.message)}
 finally{btn.disabled=false;btn.innerHTML=original;progress.wrap.remove()}
};
})();
