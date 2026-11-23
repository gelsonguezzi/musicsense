/* MusicSense 229: backing vocals automaticos sem bloquear a mesa. */
(function(){
'use strict';
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function start({dialog,url,onReady}){
 if(!dialog?.open||!url||typeof onReady!=='function')return;
 const status=document.createElement('div');
 status.className='ms229-vocal-progress';status.setAttribute('role','status');
 const label=document.createElement('span');
 label.textContent='Separando voz principal e apoios vocais em segundo plano…';
 const pct=document.createElement('strong');pct.textContent='Iniciando';
 const meter=document.createElement('progress');meter.max=100;meter.value=1;
 status.append(label,pct,meter);
 const info=dialog.querySelector('.ms226-note');
 if(info)info.after(status);else dialog.prepend(status);
 const render=(value,text)=>{
  const n=Math.max(1,Math.min(100,Math.floor(Number(value)||1)));
  meter.value=n;pct.textContent=n+'%';
  label.textContent=String(text||'Processando canais vocais');
 };
 try{
  const response=await fetch('/api/lead-backing-start',{method:'POST',
   headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
  const job=await response.json();
  if(!response.ok)throw Error(job.error||'Falha ao iniciar separacao vocal');
  if(!job.job_id)throw Error('Processo vocal nao iniciado');
  for(let i=0;i<170;i++){
   await sleep(1400);
   if(!dialog.open||!dialog.isConnected)return;
   const poll=await fetch('/api/export-progress?id='+encodeURIComponent(job.job_id),{cache:'no-store'});
   const data=await poll.json();
   if(!poll.ok)throw Error(data.error||'A separacao vocal foi interrompida');
   render(data.percent,data.stage);
   if(data.done){
    if(data.error)throw Error(data.error);
    if(!data.tracks?.lead_vocals||!data.tracks?.backing_vocals)
     throw Error('Não foram identificados dois canais vocais válidos');
    render(98,'Carregando voz principal e backing vocals na mesa');
    await onReady(data.tracks);
    render(100,'Apoios vocais prontos! Desligue Voz principal para cantar no lugar do artista.');
    return;
   }
  }
  throw Error('Etapa vocal excedeu o limite de seguranca');
 }catch(e){
  if(dialog.open) {
   meter.remove();pct.textContent='Não concluído';
   label.textContent='Seis trilhas preservadas. Detalhe vocal indisponível nesta música: '+e.message;
  }
 }
}
window.MusicSenseVocal229={start};
})();
