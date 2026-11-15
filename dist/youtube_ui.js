(function(){
  let ytPlayer=null, ytId=null, youtubeActive=false, ytReady=false;
  const $=id=>document.getElementById(id);
  const button=document.createElement('button');
  button.className='primary'; button.textContent='✦ Traduzir vídeo do YouTube';
  button.style.marginTop='10px';
  $('load').parentElement.after(button);
  const help=document.createElement('p');
  help.className='note'; help.textContent='Cole o link, abra o vídeo e clique em Traduzir. A análise pode levar alguns minutos.';
  button.after(help);
  const fallback=document.createElement('button');
  fallback.className='secondary';fallback.textContent='▶ Ouvir com tradução (sem vídeo)';
  fallback.style.marginTop='8px';fallback.style.display='none';
  help.after(fallback);
  fallback.onclick=async()=>{
    if(!ytId||!analyzed)return;
    fallback.disabled=true;fallback.textContent='⏳ Preparando áudio local...';
    $('status').textContent='Preparando reprodução local. O YouTube bloqueou o vídeo incorporado.';
    try{
      const r=await fetch('/api/youtube-playback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:'https://www.youtube.com/watch?v='+ytId})});
      const data=await r.json();if(!r.ok)throw Error(data.error||'Falha ao preparar áudio');
      youtubeActive=false;
      if(ytPlayer&&ytPlayer.destroy)try{ytPlayer.destroy()}catch{}
      ytPlayer=null;$('player').style.display='none';
      $('poster').src='https://i.ytimg.com/vi/'+ytId+'/hqdefault.jpg';$('poster').style.display='block';
      $('shade').style.pointerEvents='none';$('captions').style.pointerEvents='none';
      $('audio').src=data.audio_url;$('audio').style.display='block';
      $('status').textContent='Áudio local pronto. Pressione Play: letra e tradução acompanham a música.';
      renderSegment(0);await $('audio').play();
    }catch(e){$('status').textContent='Não foi possível reproduzir localmente: '+e.message;}
    finally{fallback.disabled=false;fallback.textContent='▶ Ouvir com tradução (sem vídeo)';}
  };
  function idFromLink(raw){
    try {
      const u=new URL(raw), h=u.hostname.toLowerCase();
      const id=h==='youtu.be'?u.pathname.split('/')[1]:
        ['youtube.com','www.youtube.com','m.youtube.com','music.youtube.com'].includes(h)?u.searchParams.get('v'):null;
      return /^[\w-]{11}$/.test(id||'')?id:null;
    }catch{return null}
  }
  function loadYouTube(){
    const id=idFromLink($('url').value.trim());
    if(!id){$('status').textContent='Cole um link válido do YouTube.';return;}
    ytId=id; youtubeActive=true; ytReady=false; analyzed=null;fallback.style.display='none';
    $('poster').style.display='none';$('audio').pause();$('audio').style.display='none';
    $('player').style.display='block';$('player').innerHTML='';
    if(window.YT && YT.Player) makePlayer(id);
    else {
      window.onYouTubeIframeAPIReady=()=>makePlayer(id);
      if(!document.getElementById('youtube-iframe-api')){
        const s=document.createElement('script');s.id='youtube-iframe-api';
        s.src='https://www.youtube.com/iframe_api';document.head.appendChild(s);
      }
    }
    $('status').textContent='Vídeo carregado. Clique em Traduzir vídeo do YouTube.';
  }
  function makePlayer(id){
    if(!youtubeActive||id!==ytId)return;
    $('player').innerHTML='';
    ytPlayer=new YT.Player('player',{
      videoId:id,playerVars:{playsinline:1,enablejsapi:1,origin:location.origin},
      events:{onReady:()=>{ytReady=true;},onError:(event)=>{fallback.style.display='inline-block';$('status').textContent='Este vídeo não pode ser reproduzido aqui (erro '+event.data+'). Use Ouvir com tradução (sem vídeo).';}}
    });
  }
  $('load').onclick=loadYouTube;
  $('file').addEventListener('change',()=>{
    youtubeActive=false; ytId=null; ytReady=false;
    if(ytPlayer && ytPlayer.destroy)try{ytPlayer.destroy()}catch{}
    ytPlayer=null;$('player').style.display='none';$('poster').style.display='';
  });
  button.onclick=async()=>{
    if(!ytId)loadYouTube();
    if(!ytId)return;
    button.disabled=true;button.textContent='⏳ Analisando YouTube...';
    const started=Date.now();
    const elapsed=setInterval(()=>{
      const sec=Math.floor((Date.now()-started)/1000);
      const min=Math.floor(sec/60);
      const phase='Preparando música e tradução';
      $('status').textContent=phase+' • Tempo decorrido: '+min+'m '+String(sec%60).padStart(2,'0')+'s. Não clique novamente.';
    },1000);
    $('status').textContent='Iniciando análise. Não clique novamente.';
    try{
      const r=await fetch('/api/youtube',{method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({url:'https://www.youtube.com/watch?v='+ytId})});
      const data=await r.json();
      if(!r.ok)throw Error(data.error||'Falha na análise do YouTube');
      // A variável analyzed pertence ao script principal.
      analyzed=data;
      fallback.style.display='inline-block';
      $('progress').max=100;$('progress').step=0.1;
      $('status').textContent='YouTube analisado: '+data.segments.length+' trechos. Tradução: '+data.translation_engine+'. Aperte Play no vídeo.';
      renderSegment(ytReady&&ytPlayer?ytPlayer.getCurrentTime():0);
    }catch(e){$('status').textContent='Erro YouTube: '+e.message;}
    finally{clearInterval(elapsed);button.disabled=false;button.textContent='✦ Traduzir vídeo do YouTube';}
  };
  setInterval(()=>{
    if(!youtubeActive||!ytReady||!ytPlayer||!analyzed)return;
    try{
      const t=ytPlayer.getCurrentTime();
      renderSegment(t);
      const duration=ytPlayer.getDuration();
      if(duration>0)$('progress').value=100*t/duration;
    }catch{}
  },250);
  $('progress').addEventListener('input',()=>{
    if(youtubeActive&&ytReady&&ytPlayer&&analyzed){
      const dur=ytPlayer.getDuration();
      if(dur>0)ytPlayer.seekTo(dur*Number($('progress').value)/100,true);
    }
  });
  $('next').addEventListener('click',()=>{
    if(youtubeActive&&ytReady&&ytPlayer&&analyzed){
      const next=analyzed.segments.find(x=>x.start>ytPlayer.getCurrentTime()+0.15);
      if(next)ytPlayer.seekTo(next.start,true);
    }
  });
  $('ball').addEventListener('change',()=>{
    if(youtubeActive&&ytReady&&ytPlayer&&analyzed)renderSegment(ytPlayer.getCurrentTime());
  });
})();