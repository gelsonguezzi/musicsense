(function(){
const $=id=>document.getElementById(id);
const files=[];const items=[];
function status(s){$('clipStatus').textContent=s}
function draw(){
 const holder=$('clipItems');holder.replaceChildren();
 items.forEach((item,i)=>{
  const row=document.createElement('div');row.style.cssText='display:flex;gap:7px;align-items:center;flex-wrap:wrap;padding:8px;border:1px solid #7775;border-radius:8px';
  const label=document.createElement('span');label.style.flex='1';label.style.minWidth='100px';label.textContent=(i+1)+'. '+item.name;
  const sec=document.createElement('input');sec.type='number';sec.min=2;sec.max=30;sec.value=item.seconds;sec.style.width='60px';sec.title='DuraÃ§Ã£o em segundos';sec.onchange=()=>item.seconds=Math.min(30,Math.max(2,Number(sec.value)||10));
  row.append(label,sec);
  for(const [txt,fn] of [['â†‘',()=>move(i,-1)],['â†“',()=>move(i,1)],['Ã—',()=>{items.splice(i,1);draw()}]]){
   const b=document.createElement('button');b.type='button';b.textContent=txt;b.title=txt==='Ã—'?'Remover':'Mudar ordem';b.onclick=fn;row.append(b);
  }
  holder.append(row);
 });
 const custom=$('clipMode').value==='custom';
 holder.querySelectorAll('input,button').forEach(e=>{if(e.textContent!=='Ã—')e.disabled=!custom});
}
function move(i,dir){const j=i+dir;if(j<0||j>=items.length)return;[items[i],items[j]]=[items[j],items[i]];draw()}
$('customClip').onclick=()=>{$('clipDialog').showModal();draw()};
$('clipMode').onchange=draw;
$('clipFiles').onchange=e=>{
 for(const file of e.target.files){
  if(items.length>=20){status('Limite de 20 materiais');break}
  const index=files.push(file)-1;
  items.push({type:'file',index,name:file.name,seconds:10});
 }
 e.target.value='';draw();
};
$('clipAddUrl').onclick=()=>{
 const url=$('clipUrl').value.trim();
 try{const u=new URL(url);if(u.protocol!=='https:')throw Error();if(items.length>=20)throw Error();
 items.push({type:'url',url,name:u.hostname+u.pathname.slice(-35),seconds:10});$('clipUrl').value='';draw();status('Imagem adicionada')}
 catch{status('Informe URL HTTPS direta de JPG, PNG ou WebP (atÃ© 20 materiais)')}
};
$('clipExport').onclick=async()=>{
 if(!analyzed?.segments?.length){status('Analise e traduza uma mÃºsica primeiro');return}
 if(!items.length){status('Adicione pelo menos uma foto ou vÃ­deo');return}
 if(!currentVideoId&&!lastFile){status('Ãudio da mÃºsica nÃ£o encontrado');return}
 const button=$('clipExport');button.disabled=true;button.textContent='Gerando MP4...';
 const wrap=$('clipProgressWrap');wrap.style.display='block';
 const show=(n,stage)=>{$('clipProgress').value=n;$('clipPercent').textContent=n+'%';$('clipStage').textContent=stage;};
 show(0,'Iniciando envio dos materiais');
 try{
  const fd=new FormData();
  files.forEach(f=>fd.append('media',f,f.name));
  if(!currentVideoId)fd.append('audio',lastFile,lastFile.name);
  const duration=Math.min(360,Math.max(1,Number(analyzed.audio_duration||analyzed.duration||activeMedia?.duration||Math.max(...analyzed.segments.map(s=>Number(s.end)||0)))));
  fd.append('settings',JSON.stringify({segments:analyzed.segments,duration,format:$('clipFormat').value,fit:$('clipFit').value,youtube_url:currentVideoId?'https://www.youtube.com/watch?v='+currentVideoId:null,items:items.map(x=>({...x,seconds:$('clipMode').value==='auto'?Number($('clipSeconds').value)||10:x.seconds}))}));
  status('Preparando materiais, montando vÃ­deo e aplicando legendas. Pode demorar alguns minutos.');
  const data=await new Promise((resolve,reject)=>{
    const xhr=new XMLHttpRequest();
    xhr.open('POST','/api/export-custom-start');
    xhr.upload.onprogress=e=>{if(e.lengthComputable)show(Math.min(3,Math.floor(e.loaded/e.total*3)),'Enviando arquivos ao servidor')};
    xhr.onerror=()=>reject(Error('Falha de conexao ao enviar arquivos'));
    xhr.onload=()=>{try{if(!xhr.responseText.trim())throw Error('Servidor interrompeu a conexao. Tente novamente.');const data=JSON.parse(xhr.responseText);if(xhr.status<200||xhr.status>=300)throw Error(data.error||'Falha no envio');resolve(data)}catch(e){reject(e)}};
    xhr.send(fd);
  });
  const job=data.job_id;
  let result;
  for(let attempt=0;attempt<1200;attempt++){
    await new Promise(resolve=>setTimeout(resolve,1000));
    const r=await fetch('/api/export-progress?id='+encodeURIComponent(job),{cache:'no-store'});
    const raw=await r.text();if(!raw.trim())throw Error('Servidor retornou resposta vazia. Confira se o MusicSense continua aberto.');const progress=JSON.parse(raw);
    if(!r.ok)throw Error(progress.error||'Falha ao consultar progresso');
    show(progress.percent||0,progress.stage||'Processando');
    if(progress.done){if(progress.error)throw Error(progress.error);result=progress;break}
  }
  if(!result)throw Error('Tempo de espera excedido');
  const dataResult=result;
  const a=document.createElement('a');a.href=dataResult.video_url;a.download='MusicSense_Personalizado_'+Date.now()+'.mp4';document.body.append(a);a.click();a.remove();status('MP4 pronto! Confira seus downloads.');
 }catch(e){status('Erro: '+e.message)}
 finally{button.disabled=false;button.textContent='Gerar videoclipe com letra'}
};
})();