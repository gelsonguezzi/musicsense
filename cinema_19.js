/* MusicSense 1.9: comandos discretos para modo cinema */
(()=>{'use strict';const v=document.getElementById('viewer');if(!v)return;
const bar=document.createElement('div');bar.className='ms19-controls';
const exit=document.createElement('button');exit.type='button';exit.textContent='✕ Sair da tela cheia';exit.setAttribute('aria-label','Sair da tela cheia');
bar.append(exit);v.append(bar);
const theater=()=>!!document.fullscreenElement||v.classList.contains('ipad-theater')||!!document.webkitFullscreenElement;
let hideTimer=null;
const show=()=>{if(!theater())return;v.classList.add('ms19-show-controls');clearTimeout(hideTimer);hideTimer=setTimeout(()=>v.classList.remove('ms19-show-controls'),3600)};
const reset=()=>{clearTimeout(hideTimer);v.classList.remove('ms19-show-controls')};
exit.addEventListener('click',async e=>{e.stopPropagation();if(document.fullscreenElement){try{await document.exitFullscreen()}catch{}}else if(document.webkitFullscreenElement&&document.webkitExitFullscreen){document.webkitExitFullscreen()}else if(v.classList.contains('ipad-theater')&&typeof setTheater==='function'){setTheater(false)}reset()});
v.addEventListener('pointerdown',e=>{if(theater()&&!e.target.closest('.ms19-controls'))show()},{passive:true});
document.addEventListener('fullscreenchange',()=>{if(theater())show();else reset()});
document.addEventListener('webkitfullscreenchange',()=>{if(theater())show();else reset()});
const m=new MutationObserver(()=>{if(theater())show();else reset()});m.observe(v,{attributes:true,attributeFilter:['class']});
window.addEventListener('orientationchange',()=>{if(theater())show()});
})();
