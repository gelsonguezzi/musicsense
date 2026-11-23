/* MusicSense 225: painel contextual com percentuais fornecidos pelo processamento real. */
(function(){
 'use strict';
 const viewer=document.getElementById('viewer');
 if(!viewer)return;
 const bubble=document.createElement('aside');
 bubble.className='ms225-processing';
 bubble.setAttribute('role','status');
 bubble.setAttribute('aria-live','polite');
 bubble.hidden=true;
 const headline=document.createElement('strong');
 const percent=document.createElement('b');
 const bar=document.createElement('progress');bar.max=100;bar.value=0;
 const row=document.createElement('div');row.className='ms225-processing-head';row.append(headline,percent);
 bubble.append(row,bar);
 viewer.append(bubble);
 let prior=null,queued=false;
 function read(){
  const all=[...document.querySelectorAll('.ms224-progress')];
  for(const el of all){
   if(!el.isConnected||!el.getClientRects().length)continue;
   const p=el.querySelector('progress');
   const label=el.querySelector('.ms224-progress-label');
   if(!p)continue;
   return {value:Math.round(Number(p.value)||0),label:(label?.textContent||'Processando').trim()};
  }
  const custom=document.getElementById('clipProgressWrap');
  if(custom&&custom.style.display!=='none'&&custom.getClientRects().length){
   const c=document.getElementById('clipProgress');
   const label=document.getElementById('clipStage');
   return {value:Math.round(Number(c?.value)||0),label:(label?.textContent||'Gerando videoclipe').trim()};
  }
  const vocals=document.getElementById('vocalSplit');
  const match=vocals?.textContent?.match(/(\d{1,3})\s*%/);
  if(match&&vocals.disabled)return {value:Math.min(100,Number(match[1])),label:'Separando voz e instrumental'};
  const status=document.getElementById('status')?.textContent||'';
  const numbered=status.match(/(?:^|\s)(\d{1,3})%/);
  if(numbered&&/(separando|analisando|exportando|baixando|renderizando|gerando|preparando)/i.test(status))
    return {value:Math.min(100,Number(numbered[1])),label:status.split(' • ').at(-1).slice(0,100)};
  return null;
 }
 function update(){
  queued=false;
  const next=read();
  const signature=next?next.value+'|'+next.label:'none';
  if(signature===prior)return;
  prior=signature;
  bubble.hidden=!next;
  if(next){
   headline.textContent=next.label;
   percent.textContent=next.value+'%';
   bar.value=next.value;
  }
 }
 function schedule(){if(!queued){queued=true;requestAnimationFrame(update)}}
 // Texto e atributos de progress atualizados durante fetch e renderizacao.
 const observer=new MutationObserver(schedule);
 observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,
  attributeFilter:['value','disabled','style']});
 schedule();
})();
