let ytAutoPlayPending=false;let ytPlayer=null,ytReady=false,ytId=null,ytActive=false,ytError=false,ytAudioUrl=null;
function youtubeId(raw){try{const u=new URL(raw),h=u.hostname.toLowerCase();const id=h==='youtu.be'?u.pathname.split('/')[1]:['youtube.com','www.youtube.com','m.youtube.com','music.youtube.com'].includes(h)?u.searchParams.get('v'):null;return /^[\w-]{11}$/.test(id||'')?id:null}catch{return null}}
function ytUrl(){return 'https://www.youtube.com/watch?v='+ytId}
function youtubeLoad(){const id=youtubeId($('url').value.trim());if(!id){setStatus('Cole um link válido do YouTube.');return false}ytId=id;currentVideoId=id;currentTitle='YouTube • '+id;ytActive=true;ytReady=false;ytAutoPlayPending=false;ytError=false;ytAudioUrl=null;analyzed=null;lastFile=null;activeMedia=null;$('video').pause();$('audio').pause();$('player').style.display='block';$('poster').style.display='none';setMediaMode('youtube');$('player').style.display='block';if(window.YT?.Player)makeYT();else{window.onYouTubeIframeAPIReady=makeYT;if(!document.getElementById('ytapi')){let s=document.createElement('script');s.id='ytapi';s.src='https://www.youtube.com/iframe_api';document.head.append(s)}}setStatus('Vídeo carregado. Clique em Traduzir vídeo do YouTube.');return true}
function makeYT(){if(!ytActive||!ytId)return;try{ytPlayer?.destroy?.()}catch{}$('player').innerHTML='';ytPlayer=new YT.Player('player',{videoId:ytId,playerVars:{playsinline:1,enablejsapi:1,origin:location.origin,rel:0,cc_load_policy:0},events:{onApiChange:()=>{try{ytPlayer.unloadModule('captions')}catch{}},onReady:()=>{ytReady=true;try{ytPlayer.unloadModule('captions')}catch{};if(ytAutoPlayPending){ytAutoPlayPending=false;try{ytPlayer.playVideo()}catch(e){}}},onError:e=>{ytError=true;ytAutoPlayPending=false;showYoutubeBlocked(e.data);setStatus('O YouTube bloqueou a incorporação (código '+e.data+'). Use Áudio + tradução ou carregue um MP4 local.')}}})}
$('load').onclick=youtubeLoad;
$('ytAnalyze').onclick=async()=>{if(ytId!==youtubeId(document.getElementById('url').value.trim())&&!youtubeLoad())return;const b=$('ytAnalyze');b.disabled=true;const started=Date.now();const timer=setInterval(()=>{const s=Math.floor((Date.now()-started)/1000);setStatus('Analisando música • '+Math.floor(s/60)+'m '+String(s%60).padStart(2,'0')+'s. Aguarde, não clique novamente.')},1000);b.textContent='⏳ Analisando...';try{const r=await fetch('/api/youtube',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:ytUrl()})});const data=await r.json();if(!r.ok)throw Error(data.error||'Falha na análise');analyzed=data;currentTitle=data.title||currentTitle;$('progress').max=100;$('progress').step=.1;renderSegment(ytReady?ytPlayer.getCurrentTime():0);setStatus('Análise concluída: '+data.segments.length+' trechos. Escolha Vídeo ou Áudio.');window.MusicSenseLibrary?.add?.(ytId,currentTitle)}catch(e){setStatus('Erro: '+e.message)}finally{clearInterval(timer);b.disabled=false;b.textContent='✦ Traduzir vídeo do YouTube'}};
async function youtubeAudio(){if(!ytId||!analyzed)return setStatus('Primeiro carregue e analise o link do YouTube.');const b=$('modeAudio');b.disabled=true;setStatus('Preparando áudio local...');try{if(!ytAudioUrl){const r=await fetch('/api/youtube-playback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:ytUrl()})});const data=await r.json();if(!r.ok)throw Error(data.error||'Falha ao preparar áudio');ytAudioUrl=data.audio_url}try{ytPlayer?.pauseVideo?.()}catch{}$('player').style.display='none';$('poster').src='https://i.ytimg.com/vi/'+ytId+'/hqdefault.jpg';activeMedia=$('audio');activeMedia.src=ytAudioUrl;setMediaMode('local-audio');$('modeAudio').classList.add('selected');$('modeVideo').classList.remove('selected');renderSegment(0);setStatus('Áudio pronto. Letra e tradução acompanham a música.');await activeMedia.play()}catch(e){setStatus('Erro: '+e.message)}finally{b.disabled=false}}
$('modeAudio').onclick=()=>{if(ytId)youtubeAudio();else if(lastFile){if(activeMedia===$('video'))setStatus('Para ouvir apenas o áudio deste MP4, use o controle de reprodução do vídeo.');else setStatus('Modo áudio ativo.')}else setStatus('Selecione uma música primeiro.')};
$('modeVideo').onclick=()=>{if(ytId){$('audio').pause();activeMedia=null;setMediaMode('youtube');$('player').style.display='block';$('modeVideo').classList.add('selected');$('modeAudio').classList.remove('selected');if(!ytError){if(ytReady&&ytPlayer?.playVideo){try{ytPlayer.playVideo()}catch(e){setStatus('Toque no Play do vídeo para iniciar.')}}else{ytAutoPlayPending=true;setStatus('Aguardando player do YouTube...')}}setStatus(ytError?'Este vídeo bloqueia reprodução incorporada. Para vídeo + tradução, use um MP4 local.':'Vídeo original selecionado. Pressione Play no YouTube.')}else if(lastFile&&activeMedia===$('video')){setMediaMode('local-video');setStatus('Vídeo local com tradução ativo.')}else setStatus('Vídeo + tradução disponível para links incorporáveis ou arquivos MP4 locais.')};
setInterval(()=>{if(sourceMode!=='youtube'||!ytReady||!ytPlayer||!analyzed)return;try{const t=ytPlayer.getCurrentTime();renderSegment(t);setProgress(t,ytPlayer.getDuration())}catch{}},200);
$('progress').addEventListener('input',()=>{if(sourceMode==='youtube'&&ytReady&&ytPlayer&&analyzed){const dur=ytPlayer.getDuration();if(dur>0)ytPlayer.seekTo(dur*Number($('progress').value)/100,true)}});
$('next').addEventListener('click',()=>{if(sourceMode==='youtube'&&ytReady&&analyzed){const next=analyzed.segments.find(x=>x.start>ytPlayer.getCurrentTime()+.15);if(next)ytPlayer.seekTo(next.start,true)}});
$('file').addEventListener('change',()=>{ytId=null;ytActive=false;ytReady=false;currentVideoId=null;ytAudioUrl=null;try{ytPlayer?.destroy?.()}catch{}ytPlayer=null;$('player').style.display='none';$('modeVideo').classList.toggle('selected',sourceMode==='local-video');$('modeAudio').classList.toggle('selected',sourceMode==='local-audio')});
// YouTube em iframe captura cliques: camada de gestos no topo permite duplo clique.
const ytGesture=$('ytGesture');
let ytClickTimer=null;
ytGesture.addEventListener('click',()=>{if(ytClickTimer)clearTimeout(ytClickTimer);ytClickTimer=setTimeout(()=>{ytClickTimer=null;try{if(!ytReady)return;const state=ytPlayer.getPlayerState();if(state===1)ytPlayer.pauseVideo();else ytPlayer.playVideo()}catch{}},230)});
ytGesture.addEventListener('dblclick',e=>{e.preventDefault();if(ytClickTimer)clearTimeout(ytClickTimer);ytClickTimer=null;fullScreen()});
function updateYtGesture(){ytGesture.style.display=sourceMode==='youtube'&&!ytError?'block':'none'}
const previousMode=setMediaMode;setMediaMode=function(mode){previousMode(mode);updateYtGesture()};

/* YouTube embedding may be forbidden by the video's owner (errors 101/150).
   Never attempt to bypass restrictions; offer working, explicit alternatives. */
function showYoutubeBlocked(code){
  if(![101,150,100,153].includes(Number(code)))return;
  const container=$('viewer');
  let notice=document.getElementById('ytBlockedNotice');
  if(!notice){
    notice=document.createElement('div');notice.id='ytBlockedNotice';
    notice.style.cssText='position:absolute;inset:0;z-index:9;background:linear-gradient(135deg,#0b1020f5,#20132ef5);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:22px;text-align:center;color:#fff';
    const title=document.createElement('strong');title.textContent='Vídeo bloqueado para reprodução incorporada';title.style.fontSize='clamp(15px,2vw,22px)';
    const desc=document.createElement('div');desc.textContent='Restrição do YouTube (código '+code+'). O modo Áudio + tradução continua disponível.';desc.style.cssText='max-width:430px;font-size:13px;line-height:1.5;color:#d2cde4';
    const actions=document.createElement('div');actions.style.cssText='display:flex;flex-wrap:wrap;gap:10px;justify-content:center';
    const audio=document.createElement('button');audio.className='btn primary';audio.textContent='♫ Ouvir com tradução';audio.onclick=()=>{if(analyzed)youtubeAudio();else setStatus('Clique primeiro em Traduzir vídeo do YouTube e depois em Áudio + tradução.')};
    const external=document.createElement('button');external.className='btn ghost';external.textContent='Abrir no YouTube';external.onclick=()=>window.open(ytUrl(),'_blank','noopener,noreferrer');
    actions.append(audio,external);notice.append(title,desc,actions);container.append(notice);
  }
  notice.style.display='flex';
}
function clearYoutubeBlocked(){const n=document.getElementById('ytBlockedNotice');if(n)n.remove()}
const oldYoutubeLoad=youtubeLoad;
youtubeLoad=function(){clearYoutubeBlocked();return oldYoutubeLoad()};
$('load').onclick=youtubeLoad;
const oldModeVideo=$('modeVideo').onclick;
$('modeVideo').onclick=function(){
  oldModeVideo();
  if(ytId&&ytError)showYoutubeBlocked(150);
};
const oldModeAudio=$('modeAudio').onclick;
$('modeAudio').onclick=function(){clearYoutubeBlocked();oldModeAudio()};
/* Search on YouTube; clipboard access is browser-permission dependent. */
(function(){
 const search=document.getElementById('ytSearchText');
 const searchBtn=document.getElementById('ytSearchGo');
 const pasteBtn=document.getElementById('ytPaste');
 const urlField=document.getElementById('url');
 let waitingForLink=false;
 function acceptLink(raw){
   const value=(raw||'').trim();
   const match=value.match(/https?:\/\/(?:www\.|m\.)?(?:youtube\.com\/watch\?[^\s]*?v=|youtu\.be\/)([A-Za-z0-9_-]{11})/i);
   if(!match)return false;
   urlField.value='https://www.youtube.com/watch?v='+match[1];
   waitingForLink=false;
   setStatus('Link do YouTube preenchido. Clique em Abrir vídeo ou Traduzir vídeo.');
   urlField.dispatchEvent(new Event('input',{bubbles:true}));
   return true;
 }
 async function pasteLink(manual){
   try{
     if(!navigator.clipboard?.readText)throw new Error('clipboard unavailable');
     const value=await navigator.clipboard.readText();
     if(!acceptLink(value)&&manual)setStatus('Copie o link de um vídeo no YouTube e tente novamente.');
   }catch(e){
     if(manual){urlField.focus();setStatus('O navegador não permitiu ler o link. Toque no campo e use Colar.');}
   }
 }
 searchBtn.addEventListener('click',()=>{
   const query=search.value.trim();
   if(!query){search.focus();return}
   waitingForLink=true;
   window.open('https://www.youtube.com/results?search_query='+encodeURIComponent(query),'_blank','noopener,noreferrer');
   setStatus('No YouTube, escolha o vídeo, copie o link e volte ao MusicSense.');
 });
 search.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();searchBtn.click()}});
 pasteBtn.addEventListener('click',()=>pasteLink(true));
 urlField.addEventListener('paste',e=>{const value=e.clipboardData?.getData('text');if(value&&acceptLink(value))e.preventDefault()});
 window.addEventListener('focus',()=>{if(waitingForLink)pasteLink(false)});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden&&waitingForLink)pasteLink(false)});
})();