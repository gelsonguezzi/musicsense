(function(){
const $=id=>document.getElementById(id);
const panel=$('ytResults'),list=$('ytResultsList'),btn=$('ytBring');
const safe=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const duration=s=>Number.isFinite(s)&&s>0?Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0'):'';
$('ytResultsClose').onclick=()=>{panel.hidden=true;document.body.classList.remove('yt-results-open')};
btn.onclick=async()=>{
const q=$('ytSearchText').value.trim();
if(q.length<2){$('ytSearchText').focus();return}
panel.hidden=false;document.body.classList.add('yt-results-open');$('ytResultsTitle').textContent='Buscando: '+q;list.innerHTML='<div class="yt-wait">Pesquisando vídeos no YouTube...</div>';btn.disabled=true;
try{
const r=await fetch('/api/youtube-search?q='+encodeURIComponent(q));const data=await r.json();
if(!r.ok)throw Error(data.error||'Erro na pesquisa');
$('ytResultsTitle').textContent='YouTube · '+q+' ('+(data.videos||[]).length+')';
if(!data.videos?.length){list.textContent='Nenhum vídeo encontrado. Tente outro termo.';return}
list.replaceChildren();
data.videos.forEach(v=>{
const card=document.createElement('button');card.type='button';card.className='yt-result';
const image=document.createElement('img');image.src='https://i.ytimg.com/vi/'+v.id+'/mqdefault.jpg';image.loading='lazy';image.alt='';
const info=document.createElement('span');info.className='yt-result-info';
const title=document.createElement('strong');title.textContent=v.title;
const channel=document.createElement('small');channel.textContent=(v.channel||'YouTube')+(duration(v.duration)?' · '+duration(v.duration):'');
info.append(title,channel);card.append(image,info);
card.onclick=()=>{$('url').value='https://www.youtube.com/watch?v='+v.id;window.youtubeLoad?.();$('ytAnalyze')?.click();panel.hidden=true;document.body.classList.remove('yt-results-open');window.scrollTo({top:0,behavior:'smooth'})};
list.append(card);
});
}catch(e){list.textContent='Não foi possível trazer os vídeos: '+e.message}
finally{btn.disabled=false}
};
})();