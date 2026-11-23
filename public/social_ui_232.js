/* MusicSense 232: compact main page, one modal for BOTH video export tools. */
(function(){
'use strict';
const buttons={lyrics:document.getElementById('exportOriginalVideo'),original:document.getElementById('downloadOriginal')};
if(!buttons.lyrics||!buttons.original)return;
const dialog=document.createElement('dialog');dialog.id='ms232Dialog';dialog.className='ms232-dialog';
dialog.innerHTML=`
<div class="ms232-head"><div><span class="ms232-kicker">MUSICSENSE / EXPORTAÇÃO</span><h2 id="ms232Title">Salvar videoclipe</h2>
<p id="ms232Help">Escolha formato, fundo e posição das legendas.</p></div>
<button id="ms232X" type="button" aria-label="Fechar">✕</button></div>
<div class="ms232-presetgrid" role="radiogroup" aria-label="Formato do vídeo">
<label><input type="radio" name="ms232Preset" value="reels"><strong>Reels / Shorts</strong><small>9:16 · 1080×1920</small></label>
<label><input type="radio" name="ms232Preset" value="feed"><strong>Feed Instagram</strong><small>4:5 · 1080×1350</small></label>
<label><input type="radio" name="ms232Preset" value="square"><strong>Quadrado</strong><small>1:1 · 1080×1080</small></label>
<label><input type="radio" name="ms232Preset" value="original"><strong>Original</strong><small>Proporção da fonte</small></label>
</div>
<div class="ms232-fields">
<label>Fundo<select id="ms232Background"><option value="blur">Vídeo desfocado</option><option value="blue">Azul MusicSense</option><option value="dark">Escuro</option></select></label>
<label id="ms232LyricsField">Legendas<select id="ms232Placement"><option value="below">Abaixo do vídeo (recomendado)</option><option value="overlay">Sobre o vídeo</option></select></label>
</div>
<div class="ms232-preview"><div id="ms232PreviewFrame"><div class="ms232-preview-video">VIDEOCLIPE</div>
<div id="ms232PreviewCaption"><b>ORIGINAL LYRICS</b><strong>Tradução em português</strong></div></div>
<p id="ms232PreviewInfo"></p></div>
<div id="ms232Progress" class="ms232-progress" hidden role="status" aria-live="polite">
<div class="ms232-progress-head"><strong id="ms232Stage">Preparando...</strong><b id="ms232Pct">0%</b></div>
<progress id="ms232Bar" max="100" value="0"></progress><div id="ms232Download"></div></div>
<div class="ms232-actions"><button id="ms232Cancel" type="button">Cancelar</button><button id="ms232Go" type="button">Gerar MP4</button></div>`;
document.body.append(dialog);
const q=x=>dialog.querySelector(x);const pause=ms=>new Promise(ok=>setTimeout(ok,ms));
let mode='lyrics',running=false;
function sourceUrl(){
 const raw=document.getElementById('url')?.value.trim()||'';
 if(raw)return raw;
 const id=(typeof currentVideoId!=='undefined'&&currentVideoId)||(typeof ytId!=='undefined'&&ytId);
 return id?'https://www.youtube.com/watch?v='+id:'';
}
function isInstagram(url){
 try{return ['instagram.com','www.instagram.com','m.instagram.com'].includes(new URL(url).hostname.toLowerCase())}catch{return false}
}
function updatePreview(){
 const preset=q('[name=ms232Preset]:checked')?.value||'reels';
 const frame=q('#ms232PreviewFrame');frame.dataset.format=preset;
 frame.dataset.background=q('#ms232Background').value;
 frame.dataset.placement=q('#ms232Placement').value;
 frame.dataset.lyrics=mode==='lyrics'?'yes':'no';
 q('#ms232PreviewInfo').textContent=mode==='lyrics'?
 'Prévia ilustrativa: clipe ampliado na largura e legendas na área inferior, sem cobrir a imagem.':
 'Sem legendas. Em Original, o vídeo não é recodificado e mantém a melhor qualidade disponível.';
}
function open(which){
 if(running)return;mode=which;
 q('#ms232Title').textContent=which==='lyrics'?'Salvar clipe + letra':'Salvar clipe original';
 const instagram=isInstagram(sourceUrl());
 q('#ms232Help').textContent=which==='lyrics'?
 'Escolha o formato e a área das legendas antes de gerar o vídeo.':
 (instagram?'Reel do Instagram detectado. Escolha o formato ou preserve o clipe original.':'Escolha o formato para Instagram ou preserve o clipe original.');
 q('#ms232LyricsField').hidden=which!=='lyrics';
 q('#ms232PreviewCaption').hidden=which!=='lyrics';
 q('[name=ms232Preset][value='+(which==='lyrics'?'reels':'original')+']').checked=true;
 q('#ms232Background').value='blur';q('#ms232Placement').value='below';
 q('#ms232Progress').hidden=true;q('#ms232Download').replaceChildren();
 q('#ms232Go').textContent='Gerar MP4';q('#ms232Go').disabled=false;
 updatePreview();dialog.showModal();
}
function progress(percent,stage,status='running'){
 const el=q('#ms232Progress');el.hidden=false;el.dataset.status=status;
 const n=Math.max(0,Math.min(100,Math.floor(Number(percent)||0)));
 q('#ms232Pct').textContent=n+'%';q('#ms232Bar').value=n;q('#ms232Stage').textContent=stage;
}
function safe(s){return String(s||'Musica').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^\w -]+/g,'').trim().replace(/\s+/g,'_').slice(0,60)||'Musica'}
async function generate(){
 if(running)return;
 const id=(typeof currentVideoId!=='undefined'&&currentVideoId)||(typeof ytId!=='undefined'&&ytId);
 const url=sourceUrl();
 const instagram=isInstagram(url);
 if(!url){progress(0,'Cole um link do YouTube ou do Instagram antes de exportar.','error');return}
 if(mode==='lyrics'&&instagram){progress(0,'Para Reel do Instagram, use Salvar clipe original. Legendas sincronizadas continuam disponíveis para vídeos já analisados do YouTube.','error');return}
 if(!id&&!instagram){progress(0,'Selecione um videoclipe do YouTube antes de exportar.','error');return}
 if(mode==='lyrics'&&!analyzed?.segments?.length){progress(0,'Traduza a música antes de salvar com legendas.','error');return}
 running=true;
 const controls=[...dialog.querySelectorAll('input,select,button')];controls.forEach(x=>x.disabled=true);
 q('#ms232Download').replaceChildren();progress(0,'Solicitando exportação...');
 const preset=q('[name=ms232Preset]:checked')?.value||'reels';
 try{
  const response=await fetch('/api/social-export-start',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({url,preset,with_lyrics:mode==='lyrics',
   segments:mode==='lyrics'?analyzed.segments:undefined,
   background:q('#ms232Background').value,placement:q('#ms232Placement').value})});
  const initial=await response.json();
  if(!response.ok||!initial.job_id)throw Error(initial.error||'Falha ao iniciar o MP4');
  let result=null;
  for(let i=0;i<900;i++){
   await pause(1300);
   const r=await fetch('/api/export-progress?id='+encodeURIComponent(initial.job_id),{cache:'no-store'});
   const status=await r.json();if(!r.ok)throw Error(status.error||'Falha na consulta');
   progress(status.percent,status.stage||'Renderizando vídeo...');
   if(status.done){if(status.error)throw Error(status.error);result=status;break}
  }
  if(!result?.video_url||!/^\/cache\/musicsense_[\w-]+\.mp4$/i.test(result.video_url))throw Error('Arquivo MP4 não disponível');
  progress(100,'Vídeo pronto para baixar!','ready');
  const a=document.createElement('a');a.href=result.video_url;
  a.download='MusicSense_'+(mode==='lyrics'?'Clipe_Legendado_':'Original_')+preset+'_'+safe(currentTitle||'Musica')+'.mp4';
  a.className='ms232-download';a.textContent='⬇ Baixar MP4 pronto';q('#ms232Download').append(a);a.click();
  q('#ms232Go').textContent='Gerar outro MP4';
 }catch(e){const percentage=Number(q('#ms232Bar').value)||0;progress(percentage,'Não foi possível concluir: '+String(e.message||'Erro desconhecido').slice(0,300),'error');q('#ms232Go').textContent='Tentar novamente'}
 finally{running=false;controls.forEach(x=>x.disabled=false)}
}
for(const el of dialog.querySelectorAll('input,select'))el.addEventListener('change',updatePreview);
q('#ms232Go').onclick=generate;
function close(){if(!running)dialog.close()}
q('#ms232X').onclick=close;q('#ms232Cancel').onclick=close;
dialog.addEventListener('cancel',e=>{if(running)e.preventDefault()});
buttons.lyrics.onclick=()=>open('lyrics');buttons.original.onclick=()=>open('original');
window.MusicSenseSocial232={open};
})();
