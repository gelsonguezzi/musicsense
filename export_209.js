window.MusicSenseExport={start:async function(mode='audio'){
 if(!analyzed?.segments?.length)return setStatus('Primeiro analise e traduza a musica.');
 const id=mode==='video'?'exportOriginalVideo':'exportVideo',b=document.getElementById(id),old=b.innerHTML;
 b.disabled=true;b.innerHTML='<span class="actionicon">⏳</span><span><strong>Gerando MP4...</strong><small>Processamento automatico</small></span>';
 try{
 let r;
 if(currentVideoId){
  setStatus(mode==='video'?'Obtendo clipe e adicionando legendas. Aguarde...':'Preparando audio e legendas. Aguarde...');
  r=await fetch(mode==='video'?'/api/export-youtube-original':'/api/export-youtube-video',
    {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:'https://www.youtube.com/watch?v='+currentVideoId,segments:analyzed.segments})});
 }else if(lastFile){
  const fd=new FormData();fd.append('file',lastFile);fd.append('segments',JSON.stringify(analyzed.segments));
  r=await fetch('/api/export-video',{method:'POST',body:fd});
 }else throw Error('Selecione e analise uma musica primeiro.');
 const data=await r.json();if(!r.ok)throw Error(data.error||'Erro na exportacao');
 const a=document.createElement('a');a.href=data.video_url;a.download=(mode==='video'?'MusicSense_Clipe_':'MusicSense_Audio_Letra_')+Date.now()+'.mp4';document.body.append(a);a.click();a.remove();
 setStatus('MP4 pronto! Confira a pasta Downloads.');
 }catch(e){setStatus('Erro ao exportar MP4: '+e.message)}
 finally{b.disabled=false;b.innerHTML=old}
}};
// Liga os botoes diretamente, mesmo se extras2.js antigo estiver em cache.
(function(){
 const audio=document.getElementById('exportVideo');
 const video=document.getElementById('exportOriginalVideo');
 if(audio)audio.onclick=()=>window.MusicSenseExport.start('audio');
 if(video)video.onclick=()=>window.MusicSenseExport.start('video');
})();
