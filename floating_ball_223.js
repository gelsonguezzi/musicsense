/* MusicSense 223: bolinha unica com trajetoria curva entre palavras. */
(function(){
 'use strict';
 const viewer=document.getElementById('viewer');
 const caption=document.getElementById('captions');
 const checkbox=document.getElementById('ball');
 if(!viewer||!caption||!checkbox)return;
 const dot=document.createElement('span');
 dot.className='ms-floating-ball-223';
 dot.setAttribute('aria-hidden','true');
 viewer.appendChild(dot);
 const state={
  fromX:0,fromY:0,toX:0,toY:0,x:0,y:0,
  start:0,duration:360,ready:false,target:null,enabled:checkbox.checked,
  lastFrame:0
 };
 const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
 function coords(element){
  const v=viewer.getBoundingClientRect(),r=element.getBoundingClientRect();
  const radius=dot.offsetWidth/2||9;
  return {
   x:clamp(r.left-v.left+r.width/2,radius+8,v.width-radius-8),
   y:clamp(r.top-v.top-Math.min(18,Math.max(10,r.height*.42)),radius+7,v.height-radius-8)
  };
 }
 function positionAt(now){
  const u=clamp((now-state.start)/state.duration,0,1);
  const eased=u*u*(3-2*u);
  const distance=Math.hypot(state.toX-state.fromX,state.toY-state.fromY);
  const arch=Math.min(58,Math.max(12,distance*.22))*Math.sin(Math.PI*u);
  return {
   x:state.fromX+(state.toX-state.fromX)*eased,
   y:state.fromY+(state.toY-state.fromY)*eased-arch
  };
 }
 function target(element,secondsToNext){
  state.enabled=checkbox.checked;
  if(!element){state.target=null;return;}
  if(!state.enabled)return;
  if(element===state.target)return;
  const now=performance.now(),p=state.ready?positionAt(now):coords(element);
  const dest=coords(element);
  state.fromX=p.x;state.fromY=p.y;
  state.toX=dest.x;state.toY=dest.y;
  state.start=now;
  const gap=Math.hypot(dest.x-p.x,dest.y-p.y);
  const available=Number.isFinite(secondsToNext)?secondsToNext*1000:520;
  // Arco perceptivel mas capaz de acompanhar palavras curtas.
  state.duration=clamp(Math.min(available*.84,250+gap*.7),130,640);
  state.ready=true;state.target=element;dot.style.opacity='1';
 }
 function frame(now){
  if(state.enabled&&state.ready&&checkbox.checked&&caption.style.display!=='none'){
   const p=positionAt(now);
   // Oscilacao vertical constante, preservando a curva de transicao.
   const dance=Math.sin(now*.012)*3.4;
   const x=clamp(p.x,12,Math.max(12,viewer.clientWidth-12));
   const y=clamp(p.y+dance,12,Math.max(12,viewer.clientHeight-12));
   dot.style.transform='translate3d('+(x-9).toFixed(2)+'px,'+(y-9).toFixed(2)+'px,0)';
   dot.style.opacity='1';
  }else dot.style.opacity='0';
  requestAnimationFrame(frame);
 }
 checkbox.addEventListener('change',()=>{
  state.enabled=checkbox.checked;
  if(!state.enabled)dot.style.opacity='0';
  if(state.enabled&&state.target){const dest=coords(state.target);state.fromX=dest.x;state.fromY=dest.y;state.toX=dest.x;state.toY=dest.y;state.start=performance.now();}
 });
 window.addEventListener('resize',()=>{
  if(state.target){const dest=coords(state.target);state.fromX=state.x=dest.x;state.fromY=state.y=dest.y;state.toX=dest.x;state.toY=dest.y;state.start=performance.now();}
 });
 window.MusicSenseBall223={target,keep:()=>{},hide:()=>{state.enabled=false;dot.style.opacity='0'},resume:()=>{state.enabled=checkbox.checked}};
 requestAnimationFrame(frame);
})();
