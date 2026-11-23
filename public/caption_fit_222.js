/* MusicSense 222: ajuste proporcional automatico das legendas dentro do quadro. */
(function(){
 const viewer=document.getElementById('viewer');
 const captions=document.getElementById('captions');
 const original=document.getElementById('original');
 const translation=document.getElementById('translation');
 if(!viewer||!captions||!original||!translation)return;
 let queued=false;
 function fit(){
  queued=false;
  if(!viewer.clientHeight||!captions.offsetWidth||captions.style.display==='none')return;
  original.style.removeProperty('font-size');
  translation.style.removeProperty('font-size');
  const originalBase=parseFloat(getComputedStyle(original).fontSize);
  const translationBase=parseFloat(getComputedStyle(translation).fontSize);
  if(!originalBase||!translationBase)return;
  const allowedHeight=Math.max(72,viewer.clientHeight*.70);
  const allowedWidth=Math.max(80,captions.clientWidth-24);
  let factor=1;
  for(let i=0;i<13;i++){
   original.style.setProperty('font-size',(originalBase*factor).toFixed(2)+'px','important');
   translation.style.setProperty('font-size',(translationBase*factor).toFixed(2)+'px','important');
   const origLineHeight=parseFloat(getComputedStyle(original).lineHeight)||originalBase*1.25;
   const transLineHeight=parseFloat(getComputedStyle(translation).lineHeight)||translationBase*1.25;
   const originalFits=original.scrollHeight<=origLineHeight*2.15;
   const translationFits=translation.scrollHeight<=transLineHeight*2.15;
   if(captions.scrollHeight<=allowedHeight &&
      original.scrollWidth<=allowedWidth+24 &&
      translation.scrollWidth<=allowedWidth+24 &&
      originalFits&&translationFits)break;
   factor*=.91;
  }
 }
 function schedule(){if(queued)return;queued=true;requestAnimationFrame(fit)}
 new MutationObserver(schedule).observe(captions,{childList:true,subtree:true,characterData:true});
 if(typeof ResizeObserver==='function')new ResizeObserver(schedule).observe(viewer);
 document.addEventListener('fullscreenchange',schedule);
 window.addEventListener('orientationchange',schedule);
 window.addEventListener('resize',schedule);
 document.fonts?.ready?.then(schedule).catch(()=>{});
 schedule();
})();
