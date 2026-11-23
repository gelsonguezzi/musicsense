/* MusicSense 225: arquivo local aparece somente se Traduzir foi clicado sem link. */
(function(){
 'use strict';
 const button=document.getElementById('ytAnalyze');
 const url=document.getElementById('url');
 const divider=document.querySelector('.divider-text');
 const chooser=document.querySelector('.uploadrow');
 const prepare=document.getElementById('analyze');
 if(!button||!url||!divider||!chooser||!prepare)return;
 const box=document.createElement('section');
 box.id='ms225-local-options';
 box.setAttribute('aria-label','Selecionar arquivo de audio ou video local');
 divider.before(box);
 box.append(divider,chooser,prepare);
 const open=(message)=>{
   box.classList.add('expanded');
   box.hidden=false;
   button.setAttribute('aria-expanded','true');
   if(message&&typeof setStatus==='function')setStatus(message);
   box.scrollIntoView({behavior:'smooth',block:'nearest'});
 };
 const close=()=>{box.classList.remove('expanded');box.hidden=true;button.setAttribute('aria-expanded','false')};
 close();
 const previous=button.onclick;
 button.onclick=function(e){
   if(!url.value.trim()){
     if(e?.preventDefault)e.preventDefault();
     open('Sem link do YouTube. Selecione um arquivo MP3, MP4 ou WAV e depois clique em Preparar arquivo com IA.');
     return;
   }
   close();
   return typeof previous==='function'?previous.call(this,e):undefined;
 };
 const file=document.getElementById('file');
 file?.addEventListener('change',()=>{if(file.files?.length)open('Arquivo selecionado. Clique em Preparar arquivo com IA.')});
 url.addEventListener('input',()=>{if(url.value.trim())close()});
})();
