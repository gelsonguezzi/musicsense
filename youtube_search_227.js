/* MusicSense 227: Enter traz resultados, 40 por pagina e visualizacoes verificadas. */
(function(){
'use strict';
const el=id=>document.getElementById(id);
const search=el('ytSearchText'),btn=el('ytBring');
const panel=el('ytResults'),list=el('ytResultsList'),title=el('ytResultsTitle');
if(!search||!btn||!panel||!list)return;
let query='',limit=40,loading=false,items=[],views=new Map(),generation=0;
const sleep=ms=>new Promise(ok=>setTimeout(ok,ms));
const duration=s=>Number.isFinite(s)&&s>0?Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0'):'';
const compact=n=>new Intl.NumberFormat('pt-BR',{notation:'compact',maximumFractionDigits:1}).format(n);
function sortItems(){
 return [...items].sort((a,b)=>{
  const x=views.get(a.id),y=views.get(b.id);
  if(Number.isFinite(x)&&Number.isFinite(y))return y-x;
  if(Number.isFinite(x))return -1;
  if(Number.isFinite(y))return 1;
  return a.index-b.index;
 });
}
function render(){
 list.replaceChildren();
 const values=sortItems();
 title.textContent='YouTube · '+query+' ('+values.length+' vídeos)';
 const note=document.createElement('div');note.className='ms227-results-note';
 const recognized=values.filter(x=>Number.isFinite(views.get(x.id))).length;
 note.textContent=recognized?
  'Visualizações verificadas: '+recognized+'/'+values.length+'. Vídeos sem dados ficam ao final.' :
  'Resultados encontrados. Consultando visualizações para ordenar os disponíveis.';
 list.append(note);
 for(const v of values){
  const card=document.createElement('button');card.type='button';card.className='yt-result';
  const image=document.createElement('img');image.src='https://i.ytimg.com/vi/'+v.id+'/mqdefault.jpg';image.loading='lazy';image.alt='';
  const info=document.createElement('span');info.className='yt-result-info';
  const name=document.createElement('strong');name.textContent=v.title;
  const channel=document.createElement('small');channel.textContent=(v.channel||'YouTube')+(duration(v.duration)?' · '+duration(v.duration):'');
  const counter=document.createElement('small');counter.className='ms227-views';
  const count=views.get(v.id);
  counter.textContent=Number.isFinite(count)?'▶ '+compact(count)+' visualizações':'Visualizações não informadas';
  info.append(name,channel,counter);card.append(image,info);
  card.onclick=()=>{
   el('url').value='https://www.youtube.com/watch?v='+v.id;
   el('url').dispatchEvent(new Event('input',{bubbles:true}));
   window.youtubeLoad?.();
   el('ytAnalyze')?.click();
   panel.hidden=true;document.body.classList.remove('yt-results-open');
   window.scrollTo({top:0,behavior:'smooth'});
  };
  list.append(card);
 }
 if(limit<120&&items.length===limit){
  const more=document.createElement('button');more.className='btn primary ms227-more';more.type='button';
  more.textContent='Localizar mais 40 vídeos';
  more.onclick=()=>load(limit+40,true);
  list.append(more);
 }
}
async function gather(ids,gen){
 const unique=[...new Set(ids.filter(id=>!views.has(id)))];
 // Os valores sao consultados em segundo plano; a busca funciona sem eles.
 for(let i=0;i<unique.length;i+=40){
  const chunk=unique.slice(i,i+40);
  try{
   const r=await fetch('/api/youtube-views-start',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({ids:chunk})});
   const response=await r.json();if(!r.ok||!response.job_id)continue;
   for(let tries=0;tries<150;tries++){
    await sleep(1400);
    if(gen!==generation)return;
    const status=await fetch('/api/export-progress?id='+encodeURIComponent(response.job_id),{cache:'no-store'});
    const data=await status.json();if(!status.ok)break;
    if(data.done){
     if(data.views){
      chunk.forEach(id=>views.set(id,Number.isFinite(data.views[id])?data.views[id]:null));
      const top=list.scrollTop;render();list.scrollTop=top;
     }
     break;
    }
    const note=list.querySelector('.ms227-results-note');
    if(note)note.textContent='Consultando visualizações: '+Math.floor(data.percent||0)+'% deste lote. Os vídeos já podem ser selecionados.';
   }
  }catch(e){console.warn('Contagem indisponível',e)}
 }
}
async function load(nextLimit=40,append=false){
 if(loading)return;
 const name=search.value.trim();
 if(name.length<2){search.focus();return}
 if(!append||name!==query){
  generation++;views=new Map();items=[];limit=40;query=name;
 }
 limit=nextLimit;
 const gen=generation;
 loading=true;btn.disabled=true;
 panel.hidden=false;document.body.classList.add('yt-results-open');
 title.textContent='Pesquisando '+limit+' vídeos: '+query;
 if(!append)list.innerHTML='<div class="yt-wait">Buscando até 40 resultados no YouTube...</div>';
 else{const more=list.querySelector('.ms227-more');if(more){more.disabled=true;more.textContent='Buscando mais vídeos...'}}
 try{
  const r=await fetch('/api/youtube-search?q='+encodeURIComponent(query)+'&limit='+limit);
  const data=await r.json();if(!r.ok)throw Error(data.error||'Pesquisa indisponível');
  if(gen!==generation)return;
  const previous=new Set(items.map(x=>x.id));
  const newly=[];
  items=(data.videos||[]).map((v,i)=>({...v,index:i}));
  for(const v of items){
   if(Number.isFinite(v.views))views.set(v.id,v.views);
   if(!previous.has(v.id))newly.push(v.id);
  }
  render();
  if(!items.length)list.textContent='Nenhum resultado encontrado.';
  else gather(newly,gen);
 }catch(e){list.textContent='Não foi possível trazer os vídeos: '+e.message}
 finally{loading=false;btn.disabled=false}
}
btn.onclick=()=>load(40,false);
search.addEventListener('keydown',event=>{
 if(event.key==='Enter'){
  event.preventDefault();event.stopImmediatePropagation();
  btn.click();
 }
},true);
window.MusicSenseSearch227={load};
})();
