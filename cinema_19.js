/* MusicSense 1.9.1: fullscreen robusto para Safari/iPad e navegadores desktop */
(function(){
'use strict';
const viewer=document.getElementById('viewer'),btn=document.getElementById('fullscreen');
if(!viewer||!btn)return;
const controls=document.createElement('div');controls.className='ms19-controls';
const exit=document.createElement('button');exit.type='button';exit.textContent='Sair da tela cheia';controls.appendChild(exit);viewer.appendChild(controls);
let timeout;
const active=()=>viewer.classList.contains('ipad-theater')||document.fullscreenElement===viewer||document.webkitFullscreenElement===viewer;
function show(){if(!active())return;viewer.classList.add('ms19-show-controls');clearTimeout(timeout);timeout=setTimeout(()=>viewer.classList.remove('ms19-show-controls'),3500)}
function update(){const on=active();btn.textContent=on?'Sair da tela cheia':'Tela cheia';if(on)show();else{clearTimeout(timeout);viewer.classList.remove('ms19-show-controls')}}
function fallback(on){viewer.classList.toggle('ipad-theater',on);document.body.classList.toggle('ipad-theater-open',on);update()}
async function toggle(){
if(viewer.classList.contains('ipad-theater')){fallback(false);return}
if(document.fullscreenElement||document.webkitFullscreenElement){
try{if(document.exitFullscreen)await document.exitFullscreen();else if(document.webkitExitFullscreen)document.webkitExitFullscreen();else fallback(false)}catch{fallback(false)}
update();return
}
try{
if(viewer.requestFullscreen){await viewer.requestFullscreen();update();return}
if(viewer.webkitRequestFullscreen){viewer.webkitRequestFullscreen();update();return}
}catch(e){}
fallback(true)
}
btn.onclick=toggle;
exit.addEventListener('click',e=>{e.stopPropagation();toggle()});
viewer.addEventListener('pointerdown',e=>{if(active()&&!e.target.closest('.ms19-controls'))show()},{passive:true});
document.addEventListener('fullscreenchange',update);
document.addEventListener('webkitfullscreenchange',update);
window.addEventListener('orientationchange',()=>{if(active())show()});
viewer.addEventListener('dblclick',e=>{e.stopImmediatePropagation();toggle()},true);
let lastTap=0;
viewer.addEventListener('touchend',e=>{if(e.changedTouches.length!==1||e.target.closest('button,input,video,a'))return;const now=Date.now();if(now-lastTap<330){e.preventDefault();e.stopImmediatePropagation();lastTap=0;toggle()}else lastTap=now},{capture:true,passive:false});
update();
})();
