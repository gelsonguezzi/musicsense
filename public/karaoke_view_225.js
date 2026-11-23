/* MusicSense 225: frases musicais e progresso de traducao sincronizado. */
(function(){
'use strict';
const cache=new WeakMap();
const num=x=>Number(x)||0;
function wordsOf(seg){
 return (Array.isArray(seg.words)?seg.words:[]).filter(w=>w&&String(w.text??w.word??'').trim()&&Number.isFinite(Number(w.start))).map(w=>({...w,text:String(w.text??w.word).trim(),start:num(w.start),end:num(w.end)}));
}
function splitAt(text,ratio){
 const items=String(text||'').trim().split(/\s+/);
 if(items.length<4)return [String(text||''),''];
 const index=Math.max(1,Math.min(items.length-1,Math.round(items.length*ratio)));
 // Prioriza uma virgula, ponto ou ponto e virgula proximo da pausa musical.
 let best=index,dist=1e9;
 items.forEach((word,i)=>{
  if(i<1||i>items.length-3||!/[,:;.!?]$/.test(word))return;
  const diff=Math.abs(i+1-index);
  if(diff<dist){best=i+1;dist=diff}
 });
 if(dist>2)best=index;
 return [items.slice(0,best).join(' '),items.slice(best).join(' ')];
}
function divide(seg){
 const words=wordsOf(seg);
 if(words.length<5||!seg.translation)return [seg];
 const breaks=[];
 for(let i=2;i<words.length-2;i++){
  const gap=words[i].start-words[i-1].end;
  const punct=/[,;.!?]$/.test(words[i-1].text);
  if(gap>=.38||(punct&&gap>=.15)){
   // Pausas reais entre frases, sem quebrar um canto continuo.
   if(words[i-1].end-num(seg.start)>=.65&&num(seg.end)-words[i].start>=.65)breaks.push(i);
  }
 }
 if(!breaks.length)return [seg];
 // Maximo 3 trechos por bloco; em frases sem pausa nao altera a musica.
 const indexes=[0,...breaks.slice(0,2),words.length];
 const parts=[];let leftover=String(seg.translation||'');
 for(let k=0;k<indexes.length-1;k++){
  const a=indexes[k],b=indexes[k+1];
  const chunk=words.slice(a,b);
  let translation=leftover;
  if(k<indexes.length-2){
   const restCount=words.length-a;
   const pair=splitAt(leftover,chunk.length/restCount);
   translation=pair[0];leftover=pair[1];
  }
  if(!translation.trim())return [seg];
  parts.push({
   ...seg,start:Math.max(num(seg.start),chunk[0].start),
   end:k===indexes.length-2?num(seg.end):Math.max(chunk.at(-1).end,words[b]?.start||0),
   original:chunk.map(x=>x.text).join(' '),
   translation:translation.trim(),words:chunk,
   _visualSplit225:true
  });
 }
 return parts;
}
function segments(data){
 if(!data||!Array.isArray(data.segments))return [];
 const old=cache.get(data);
 if(old&&old.source===data.segments)return old.value;
 const value=data.segments.flatMap(divide);
 cache.set(data,{source:data.segments,value});
 return value;
}
const el=document.getElementById('translation');
let current=null,spans=[],lastBreak=-1;
function renderTranslation(seg,time){
 const text=String(seg.translation||'Tradução indisponível').trim();
 const words=text.split(/\s+/).filter(Boolean);
 if(!words.length){el.replaceChildren();current=null;spans=[];return}
 const original=document.getElementById('original');
 let breakIndex=-1;
 const originals=[...original.querySelectorAll('.karaoke-word')];
 if(originals.length>1){
  const tops=originals.map(n=>Math.round(n.getBoundingClientRect().top));
  const index=tops.findIndex((top,i)=>i>0&&top>tops[0]+3);
  if(index>0){
   breakIndex=Math.max(1,Math.min(words.length-1,Math.round(words.length*index/originals.length)));
   if(words.length<3)breakIndex=-1;
  }
 }
 if(current!==seg||lastBreak!==breakIndex||spans.length!==words.length){
  el.replaceChildren();spans=[];lastBreak=breakIndex;current=seg;
  const fragment=document.createDocumentFragment();
  words.forEach((word,i)=>{
   if(i===breakIndex)fragment.append(document.createElement('br'));
   const span=document.createElement('span');span.textContent=word+(i===words.length-1?'':' ');
   span.className='pt-pending';spans.push(span);fragment.append(span);
  });
  el.append(fragment);
 }
 const source=(seg.words||[]).filter(w=>Number.isFinite(Number(w.start)));
 const start=num(seg.start),end=Math.max(start+.1,num(seg.end));
 const timeRatio=Math.max(0,Math.min(1,(time-start)/(end-start)));
 const wordRatio=source.length?Math.max(0,Math.min(1,source.filter(w=>time>=Number(w.start)).length/source.length)):timeRatio;
 const fraction=Math.max(0,Math.min(1,.65*wordRatio+.35*timeRatio));
 const filled=Math.floor(words.length*fraction);
 spans.forEach((span,i)=>{
  const mode=i<filled?'pt-active':i===filled&&fraction>0?'pt-playing':'pt-pending';
  if(span.className!==mode)span.className=mode;
 });
}
window.MusicSenseView225={segments,renderTranslation};
})();
