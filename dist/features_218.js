/* MusicSense 218: original video and local six-track mixer. */
(function(){
 const byId=id=>document.getElementById(id);
 const url=()=>{const id=(typeof ytId!=='undefined'&&ytId)||(typeof currentVideoId!=='undefined'&&currentVideoId);return id?'https://www.youtube.com/watch?v='+id:null};
 const status=msg=>{if(typeof setStatus==='function')setStatus(msg)};
 const wait=ms=>new Promise(r=>setTimeout(r,ms));
 async function job(route,onProgress){
  const source=url();if(!source)throw Error('Cole um link do YouTube primeiro.');
  const res=await fetch(route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:source})});
  const data=await res.json();if(!res.ok)throw Error(data.error||'Erro ao iniciar');
  for(let i=0;i<3600;i++){await wait(1000);const p=await fetch('/api/export-progress?id='+encodeURIComponent(data.job_id),{cache:'no-store'});const j=await p.json();onProgress?.(j);if(j.done){if(j.error)throw Error(j.error);return j}}
  throw Error('Tempo limite excedido');
 }
 const download=(href,name)=>{const a=document.createElement('a');a.href=href;a.download=name;document.body.append(a);a.click();a.remove()};
 const original=byId('downloadOriginal');
 if(original)original.onclick=async()=>{
  const old=original.innerHTML;original.disabled=true;
  try{
   const r=await job('/api/download-original',p=>{status('Baixando clipe original: '+(p.percent||0)+'% • '+(p.stage||''))});
   download(r.video_url,'MusicSense_Clipe_Original.mp4');status('Clipe original pronto. Verifique Downloads.');
  }catch(e){status('Erro ao baixar clipe: '+e.message)}
  finally{original.disabled=false;original.innerHTML=old}
 };
 const button=byId('separateSix');
 if(!button)return;
 button.onclick=async()=>{
  const old=button.innerHTML;button.disabled=true;
  try{
   const result=await job('/api/separate-six',p=>status('Separando instrumentos: '+(p.percent||0)+'% • '+(p.stage||'')));
   const tracks=result.tracks||{};const keys=['vocals','drums','bass','guitar','piano','other'];
   const names={vocals:'Voz',drums:'Bateria',bass:'Baixo',guitar:'Guitarra',piano:'Piano',other:'Outros instrumentos'};
   const dialog=document.createElement('dialog');dialog.className='modal ms-mixer';
   const title=document.createElement('h2');title.textContent='Mesa de instrumentos';dialog.append(title);
   const intro=document.createElement('p');intro.textContent='Ative ou silencie as trilhas enquanto a música toca. Os instrumentos são estimativas da IA.';dialog.append(intro);
   const audios={};const inputs={};
   const master=document.createElement('div');master.className='mixer-controls';
   const play=document.createElement('button');play.className='btn primary';play.textContent='▶ Reproduzir';
   const stop=document.createElement('button');stop.className='btn ghost';stop.textContent='■ Parar';
   const close=document.createElement('button');close.className='btn ghost';close.textContent='Fechar';
   master.append(play,stop,close);dialog.append(master);
   const seek=document.createElement('input');seek.type='range';seek.min='0';seek.max='100';seek.step='.1';seek.value='0';seek.style.width='100%';dialog.append(seek);
   const clock=document.createElement('p');clock.textContent='00:00';dialog.append(clock);
   const tracksWrap=document.createElement('div');tracksWrap.className='mixer-tracks';dialog.append(tracksWrap);
   keys.forEach(key=>{
    if(!tracks[key])return;
    const audio=new Audio(tracks[key]);audio.preload='metadata';audios[key]=audio;
    const row=document.createElement('div');row.className='mixer-row';
    const label=document.createElement('strong');label.textContent=names[key];
    const mute=document.createElement('button');mute.className='btn ghost small';mute.textContent='M';mute.title='Silenciar / ativar';
    const solo=document.createElement('button');solo.className='btn ghost small';solo.textContent='S';solo.title='Ouvir somente esta trilha';
    const vol=document.createElement('input');vol.type='range';vol.min='0';vol.max='100';vol.value='80';vol.setAttribute('aria-label','Volume de '+names[key]);inputs[key]={mute:false,solo:false,volume:vol};
    const dl=document.createElement('button');dl.className='btn ghost small';dl.textContent='⬇ MP3';dl.onclick=()=>download(tracks[key],'MusicSense_'+key+'.mp3');
    mute.onclick=()=>{inputs[key].mute=!inputs[key].mute;mute.classList.toggle('mixer-active',inputs[key].mute);updateVolumes()};
    solo.onclick=()=>{inputs[key].solo=!inputs[key].solo;solo.classList.toggle('mixer-active',inputs[key].solo);updateVolumes()};
    vol.oninput=updateVolumes;row.append(label,mute,solo,vol,dl);tracksWrap.append(row);
   });
   function updateVolumes(){const anySolo=Object.values(inputs).some(x=>x.solo);keys.forEach(k=>{if(audios[k])audios[k].volume=inputs[k].mute||(anySolo&&!inputs[k].solo)?0:Number(inputs[k].volume.value)/100})}
   updateVolumes();
   let playing=false;const main=audios.vocals||Object.values(audios)[0];
   play.onclick=async()=>{if(playing){Object.values(audios).forEach(a=>a.pause());playing=false;play.textContent='▶ Reproduzir';return}
    const time=main.currentTime;for(const a of Object.values(audios))a.currentTime=time;
    try{await Promise.all(Object.values(audios).map(a=>a.play()));playing=true;play.textContent='Ⅱ Pausar'}catch(e){status('Reprodução bloqueada: '+e.message)}
   };
   stop.onclick=()=>{Object.values(audios).forEach(a=>{a.pause();a.currentTime=0});playing=false;play.textContent='▶ Reproduzir';seek.value=0};
   seek.oninput=()=>{const duration=main.duration||0;const time=duration*Number(seek.value)/100;Object.values(audios).forEach(a=>{if(a.readyState)a.currentTime=time})};
   const interval=setInterval(()=>{if(!dialog.isConnected){clearInterval(interval);return}const duration=main.duration||0,time=main.currentTime||0;if(duration)seek.value=100*time/duration;clock.textContent=String(Math.floor(time/60)).padStart(2,'0')+':'+String(Math.floor(time%60)).padStart(2,'0');if(playing)Object.values(audios).forEach(a=>{if(a!==main&&Math.abs(a.currentTime-time)>.15)a.currentTime=time})},250);
   close.onclick=()=>dialog.close();
   dialog.addEventListener('close',()=>{clearInterval(interval);Object.values(audios).forEach(a=>{a.pause();a.src=''});dialog.remove()});
   document.body.append(dialog);dialog.showModal();status('Seis trilhas prontas. Mesa de mixagem aberta.');
  }catch(e){status('Erro na separação por instrumentos: '+e.message)}
  finally{button.disabled=false;button.innerHTML=old}
 };
})();
