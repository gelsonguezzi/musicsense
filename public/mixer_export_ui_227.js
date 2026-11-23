/* MusicSense 227: exportar selecao S e efeitos de voz em tempo real. */
(function(){
'use strict';
const $=id=>document.getElementById(id);
const sleep=ms=>new Promise(ok=>setTimeout(ok,ms));
function button(label,variant='ghost'){
 const b=document.createElement('button');b.type='button';b.className='btn '+variant;
 b.textContent=label;return b;
}
function selector(label,opts){
 const wrap=document.createElement('label');wrap.className='ms227-option';
 const span=document.createElement('span');span.textContent=label;
 const select=document.createElement('select');
 for(const [value,caption] of opts){const op=document.createElement('option');op.value=value;op.textContent=caption;select.add(op)}
 wrap.append(span,select);return {wrap,select};
}
function effects(context,gains,available){
 const key=available.includes('lead_vocals')?'lead_vocals':available.includes('vocals')?'vocals':null;
 const flags={echo:false,reverb:false};
 if(!key)return {flags,available:false};
 const src=gains[key];
 const delay=context.createDelay(1.0);delay.delayTime.value=.19;
 const feedback=context.createGain();feedback.gain.value=.22;
 const echoWet=context.createGain();echoWet.gain.value=0;
 src.connect(delay);delay.connect(feedback);feedback.connect(delay);
 delay.connect(echoWet);echoWet.connect(context.destination);
 const conv=context.createConvolver();
 const rate=context.sampleRate;
 const frames=Math.floor(rate*1.65);
 const impulse=context.createBuffer(2,frames,rate);
 for(let c=0;c<2;c++){
  const data=impulse.getChannelData(c);
  for(let i=0;i<frames;i++){
   const decay=Math.pow(1-i/frames,2.7);
   data[i]=(Math.random()*2-1)*decay;
  }
 }
 conv.buffer=impulse;
 const revWet=context.createGain();revWet.gain.value=0;
 src.connect(conv);conv.connect(revWet);revWet.connect(context.destination);
 const set=(name,on)=>{
  flags[name]=!!on;
  const node=name==='echo'?echoWet:revWet;
  node.gain.setTargetAtTime(on?(name==='echo'?.24:.19):0,context.currentTime,.025);
 };
 return {flags,available:true,set,rebindLead(gain){gain.connect(delay);gain.connect(conv)}};
}
function attach(api){
 const {dialog,controls,context,gains,available,tracks,inputs}=api;
 const saveZip=button('⬇ Salvar multitrilhas','ghost');
 const saveMP4=button('🎬 Salvar MP4 + legendas','primary');
 controls.append(saveZip,saveMP4);
 const format=selector('Formato de vídeo',[
  ['original','Original'],['1:1','1:1 • Quadrado'],['16:9','16:9 • Horizontal'],['9:16','9:16 • Vertical']
 ]);
 const background=selector('Fundo do MP4',[
  ['blue','Azul'],['video','Videoclipe original']
 ]);
 const options=document.createElement('div');options.className='ms227-options';
 options.append(format.wrap,background.wrap);
 controls.insertAdjacentElement('afterend',options);
 const fx=effects(context,gains,available);
 const voiceBox=document.createElement('div');voiceBox.className='ms227-fx';
 const info=document.createElement('span');info.textContent='Efeitos da voz (somente na mixagem):';
 voiceBox.append(info);
 for(const [name,title] of [['echo','Eco'],['reverb','Reverberação']]){
  const item=document.createElement('label');item.className='ms227-check';
  const check=document.createElement('input');check.type='checkbox';
  check.disabled=!fx.available;
  const caption=document.createElement('span');caption.textContent=title;
  item.append(check,caption);voiceBox.append(item);
  check.addEventListener('change',()=>fx.set(name,check.checked));
 }
 if(!fx.available){
  const note=document.createElement('small');note.textContent='Não há trilha vocal nesta música.';voiceBox.append(note);
 }
 options.after(voiceBox);
 const help=document.createElement('p');help.className='ms227-help';
 help.textContent='Marque S nas trilhas que deseja salvar. Várias trilhas podem ter S ativo ao mesmo tempo. ZIP inclui MP3s separados e mixagem; MP4 inclui a mixagem e os dois idiomas.';
 voiceBox.after(help);
 const progress=document.createElement('div');progress.className='ms224-progress ms227-job';
 progress.hidden=true;
 const stage=document.createElement('div');stage.className='ms224-progress-label';
 const bar=document.createElement('progress');bar.max=100;bar.value=0;
 const pct=document.createElement('strong');pct.textContent='0%';
 progress.append(stage,bar,pct);help.after(progress);
 const selected=()=>{
  const chosen=available.filter(k=>inputs[k].solo&&inputs[k].on&&!inputs[k].mute);
  if(!chosen.length)throw Error('Ative S nas trilhas desejadas. É possível selecionar mais de uma.');
  return chosen.map(key=>({
   url:tracks[key],label:inputs[key].toggle.textContent,
   volume:Number(inputs[key].volume.value)/100
  }));
 };
 const controlsToDisable=[saveZip,saveMP4,format.select,background.select];
 async function submit(mode){
  const oldLabel=mode==='zip'?saveZip.textContent:saveMP4.textContent;
  try{
   const chosen=selected();
   if(mode==='mp4'&&(!analyzed?.segments?.length))
    throw Error('Traduza a música antes de gerar um MP4 com legendas.');
   if(mode==='mp4'&&background.select.value==='video'&&!currentVideoId)
    throw Error('Videoclipe original só está disponível quando a origem é YouTube.');
   progress.hidden=false;
   const update=(v,s)=>{
    const n=Math.max(0,Math.min(100,Math.floor(Number(v)||0)));
    bar.value=n;pct.textContent=n+'%';stage.textContent=s||'Preparando';
   };
   update(1,'Iniciando exportação');
   controlsToDisable.forEach(b=>b.disabled=true);
   const payload={
    mode,selected:chosen,format:format.select.value,background:background.select.value,
    youtube_url:currentVideoId?'https://www.youtube.com/watch?v='+currentVideoId:'',
    segments:mode==='mp4'?analyzed.segments:undefined,
    effects:fx.flags
   };
   const response=await fetch('/api/mixer-export-start',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
   const started=await response.json();
   if(!response.ok)throw Error(started.error||'Falha ao iniciar exportação');
   let result;
   for(let i=0;i<3600;i++){
    await sleep(1000);
    const poll=await fetch('/api/export-progress?id='+encodeURIComponent(started.job_id),{cache:'no-store'});
    const state=await poll.json();
    if(!poll.ok)throw Error(state.error||'Falha ao consultar progresso');
    update(state.percent,state.stage);
    if(state.done){if(state.error)throw Error(state.error);result=state;break}
   }
   if(!result)throw Error('Exportação excedeu o tempo limite');
   if(!result.file_url)throw Error('O servidor não retornou o arquivo.');
   const a=document.createElement('a');a.href=result.file_url;a.download=result.filename||'MusicSense_Export';
   document.body.append(a);a.click();a.remove();
   if(typeof setStatus==='function')setStatus('Exportação concluída: '+chosen.length+' trilhas selecionadas.');
   update(100,'Arquivo pronto. Confira Downloads.');
  }catch(e){
   progress.hidden=false;stage.textContent='Erro: '+e.message;
   if(typeof setStatus==='function')setStatus('Exportação: '+e.message);
  }finally{
   controlsToDisable.forEach(b=>b.disabled=false);
   if(mode==='zip')saveZip.textContent=oldLabel;else saveMP4.textContent=oldLabel;
  }
 }
 saveZip.onclick=()=>submit('zip');
 saveMP4.onclick=()=>submit('mp4');
 return fx;
}
window.MusicSenseMixer227={attach};
})();
