/* MusicSense 224 - progresso verificavel da transcricao e traducao. */
(function(){
 'use strict';
 const get=id=>document.getElementById(id);
 const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 function progressElement(button){
  const element=document.createElement('div');element.className='ms224-progress';
  element.setAttribute('role','status');
  const caption=document.createElement('div');caption.className='ms224-progress-label';
  const meter=document.createElement('progress');meter.max=100;meter.value=0;
  const counter=document.createElement('strong');counter.textContent='0%';
  element.append(caption,meter,counter);
  button.insertAdjacentElement('afterend',element);
  return {element,update(p,s){
   const v=Math.min(100,Math.max(0,Math.round(Number(p)||0)));
   meter.value=v;counter.textContent=v+'%';caption.textContent=s||'Processando';
  },close(){element.remove()}};
 }
 async function poll(id,notify){
  for(let i=0;i<3600;i++){
   await delay(1000);
   const response=await fetch('/api/export-progress?id='+encodeURIComponent(id),{cache:'no-store'});
   const j=await response.json();
   if(!response.ok)throw Error(j.error||'Falha ao consultar progresso');
   notify(j.percent,j.stage);
   if(j.done){if(j.error)throw Error(j.error);return j.result}
  }
  throw Error('A analise ultrapassou o tempo limite.');
 }
 const youtube=get('ytAnalyze');
 if(youtube)youtube.onclick=async()=>{
  if(typeof youtubeId!=='function'||typeof youtubeLoad!=='function')return;
  if(ytId!==youtubeId(get('url').value.trim())&&!youtubeLoad())return;
  const old=youtube.textContent;
  youtube.disabled=true;
  const p=progressElement(youtube);
  try{
   p.update(1,'Conectando ao servidor de IA');
   const res=await fetch('/api/youtube-start',{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({url:ytUrl()})});
   const data=await res.json();
   if(!res.ok)throw Error(data.error||'Nao foi possivel iniciar a analise');
   const result=await poll(data.job_id,(n,stage)=>{
    p.update(n,stage);
    youtube.textContent='⏳ '+Math.floor(Number(n)||0)+'%';
    if(typeof setStatus==='function')setStatus('Analisando musica: '+Math.floor(Number(n)||0)+'% • '+stage);
   });
   analyzed=result;currentTitle=result.title||currentTitle;
   get('progress').max=100;get('progress').step=.1;
   renderSegment(ytReady?ytPlayer.getCurrentTime():0);
   setStatus('Analise concluida: '+result.segments.length+' trechos.');
   window.MusicSenseLibrary?.add?.(ytId,currentTitle);
  }catch(err){setStatus('Erro: '+err.message)}
  finally{youtube.disabled=false;youtube.textContent=old;p.close()}
 };
 const local=get('analyze');
 if(local)local.onclick=async()=>{
  if(!lastFile)return;
  const old=local.textContent;
  local.disabled=true;
  const p=progressElement(local);
  try{
   p.update(0,'Enviando arquivo local');
   const job=await new Promise((resolve,reject)=>{
    const xhr=new XMLHttpRequest();
    xhr.open('POST','/api/analyze-start');
    xhr.upload.onprogress=e=>{
     if(e.lengthComputable)p.update(Math.min(8,Math.floor(8*e.loaded/e.total)),'Enviando arquivo');
    };
    xhr.onerror=()=>reject(Error('Falha de conexao no envio'));
    xhr.onload=()=>{
     try{const x=JSON.parse(xhr.responseText);if(xhr.status<200||xhr.status>=300)throw Error(x.error||'Falha ao enviar');resolve(x.job_id)}
     catch(e){reject(e)}
    };
    const body=new FormData();body.append('file',lastFile,lastFile.name);
    xhr.send(body);
   });
   const result=await poll(job,(n,s)=>{
    p.update(n,s);
    local.textContent='⏳ '+Math.floor(Number(n)||0)+'%';
    setStatus('Analisando arquivo: '+Math.floor(Number(n)||0)+'% • '+s);
   });
   analyzed=result;get('progress').max=100;get('progress').step=.1;
   renderSegment(0);
   setStatus('Concluido: '+result.segments.length+' trechos. Traducao: '+result.translation_engine);
  }catch(e){setStatus('Erro: '+e.message)}
  finally{local.disabled=false;local.textContent=old;p.close()}
 };
})();
