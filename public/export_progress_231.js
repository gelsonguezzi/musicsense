/* MusicSense 231 - exportacao monitorada, status dentro do card e download recuperavel. */
(function(){
'use strict';
const sleep=t=>new Promise(ok=>setTimeout(ok,t));
const buttons={
 audio:document.getElementById('exportVideo'),
 video:document.getElementById('exportOriginalVideo')
};
const errors={};
function panel(button){
 let root=button.nextElementSibling;
 if(!root?.classList?.contains('ms231-export-status')){
  root=document.createElement('div');
  root.className='ms231-export-status';
  root.setAttribute('role','status');
  root.setAttribute('aria-live','polite');
  const heading=document.createElement('div');heading.className='ms231-status-top';
  const message=document.createElement('strong');message.className='ms231-status-message';
  const percent=document.createElement('b');percent.className='ms231-status-percent';
  const bar=document.createElement('progress');bar.max=100;bar.value=0;
  const action=document.createElement('div');action.className='ms231-status-actions';
  heading.append(message,percent);root.append(heading,bar,action);button.after(root);
 }
 return {root,message:root.querySelector('.ms231-status-message'),
   percent:root.querySelector('.ms231-status-percent'),
   bar:root.querySelector('progress'),
   action:root.querySelector('.ms231-status-actions')};
}
function showMessage(mode,message,kind='error'){
 const button=buttons[mode];if(!button)return;
 const ui=panel(button);ui.root.hidden=false;
 ui.root.dataset.status=kind;
 ui.message.textContent=message;
 ui.percent.textContent=kind==='error'?'Verificar':'';
 ui.bar.hidden=true;ui.action.replaceChildren();
 if(typeof setStatus==='function')setStatus(message);
}
function safeName(text){
 return String(text||'Musica').normalize('NFD').replace(/[\u0300-\u036f]/g,'')
  .replace(/[^\w -]+/g,'').trim().replace(/\s+/g,'_').slice(0,75)||'Musica';
}
async function start(mode='video'){
 if(mode!=='video'&&mode!=='audio')return;
 const button=buttons[mode];if(!button||button.disabled)return;
 // A falta de analise e indicada JUNTO ao botao. Nada de clique silencioso.
 if(!analyzed?.segments?.length){
  showMessage(mode,'Primeiro clique em Traduzir e aguarde a letra ficar pronta.');
  return;
 }
 const id=typeof currentVideoId!=='undefined'&&currentVideoId;
 const file=typeof lastFile!=='undefined'&&lastFile;
 if(!id&&!file){
  showMessage(mode,'Selecione uma musica do YouTube ou um arquivo local.');
  return;
 }
 if(mode==='video'&&!id){
  showMessage(mode,'Salvar clipe + letra exige videoclipe do YouTube. Para arquivo local, use Salvar audio + letra.');
  return;
 }
 const old=button.innerHTML;
 const ui=panel(button);
 ui.root.hidden=false;ui.root.dataset.status='running';
 ui.bar.hidden=false;ui.bar.value=0;ui.action.replaceChildren();
 let lastPercent=-1;
 const update=(amount,description)=>{
  const value=Math.max(0,Math.min(100,Math.floor(Number(amount)||0)));
  ui.bar.value=value;
  ui.percent.textContent=value+'%';
  ui.message.textContent=description||'Processando o videoclipe';
  button.innerHTML='<span class="actionicon">⏳</span><span><strong>'+value+'% • Gerando MP4</strong><small>'+
    (mode==='video'?'Videoclipe original e tradução':'Áudio e tradução')+'</small></span>';
  if(value!==lastPercent){
   lastPercent=value;
   if(typeof setStatus==='function')setStatus('Exportação MP4: '+value+'% • '+(description||'Em andamento'));
  }
 };
 let failed=false;
 try{
  button.disabled=true;
  update(0,'Enviando pedido ao servidor...');
  let job;
  if(id){
   const abort=new AbortController();
   const timeout=setTimeout(()=>abort.abort(),35000);
   try{
    const response=await fetch('/api/export-video-start',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({url:'https://www.youtube.com/watch?v='+id,
       mode,segments:analyzed.segments,title:currentTitle||'',language:analyzed.language||'en'}),
      signal:abort.signal
    });
    const result=await response.json();
    if(!response.ok)throw Error(result.error||'Nao foi possivel iniciar exportação');
    job=result.job_id;
   }finally{clearTimeout(timeout)}
  }else{
   job=await new Promise((resolve,reject)=>{
    const xhr=new XMLHttpRequest();
    xhr.open('POST','/api/export-video-start');
    xhr.timeout=120000;
    xhr.upload.onprogress=e=>{
     if(e.lengthComputable)update(Math.min(4,Math.floor(4*e.loaded/e.total)),'Enviando arquivo local...');
    };
    xhr.onerror=()=>reject(Error('Conexão perdida durante envio.'));
    xhr.ontimeout=()=>reject(Error('Envio excedeu o limite de tempo.'));
    xhr.onload=()=>{
     try{
      const data=JSON.parse(xhr.responseText);
      if(xhr.status<200||xhr.status>=300)throw Error(data.error||'Falha de envio');
      resolve(data.job_id);
     }catch(e){reject(e)}
    };
    const body=new FormData();body.append('file',file,file.name);
    body.append('segments',JSON.stringify(analyzed.segments));xhr.send(body);
   });
  }
  if(!job)throw Error('Servidor nao retornou identificador do processamento.');
  update(Math.max(1,lastPercent),'Pedido recebido. Preparando videoclipe...');
  let final=null;
  for(let i=0;i<1200;i++){
   await sleep(1300);
   const response=await fetch('/api/export-progress?id='+encodeURIComponent(job),{cache:'no-store'});
   const data=await response.json();
   if(!response.ok)throw Error(data.error||'Falha ao acompanhar exportação');
   update(data.percent,data.stage||'Renderizando videoclipe...');
   if(data.done){
    if(data.error)throw Error(data.error);
    final=data;break;
   }
  }
  if(!final?.video_url)throw Error('A exportação nao retornou um MP4 válido.');
  // Primeiro valida o download sem baixar o arquivo inteiro.
  const url=final.video_url;
  if(!/^\/cache\/musicsense_[a-z0-9_-]+\.mp4$/i.test(url)){
   throw Error('Endereço de download invalido.');
  }
  update(100,'MP4 pronto! Clique para baixar caso o navegador nao inicie o download.');
  ui.root.dataset.status='ready';
  const link=document.createElement('a');link.href=url;
  link.download='MusicSense_'+(mode==='video'?'Clipe_Letra_':'Audio_Letra_')+safeName(currentTitle||'Musica')+'.mp4';
  link.className='ms231-download-link';link.textContent='⬇ Baixar MP4 pronto';
  ui.action.append(link);
  // Automatic download with a manual fallback always visible.
  link.click();
  if(typeof setStatus==='function')setStatus('MP4 pronto. Se nao iniciou o download, use o link abaixo do botão.');
 }catch(e){
  failed=true;
  showMessage(mode,'Falha no MP4: '+(e.name==='AbortError'?'Conexão excedeu o tempo limite.':e.message));
 }finally{
  button.disabled=false;
  button.innerHTML=old;
  if(failed)ui.root.dataset.status='error';
 }
}
window.MusicSenseExport=window.MusicSenseExport||{};
window.MusicSenseExport.start=start;
for(const [mode,button] of Object.entries(buttons)){
 if(button)button.onclick=()=>start(mode);
}
})();