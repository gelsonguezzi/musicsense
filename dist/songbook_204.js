(function(){
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=v=>String(v||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,' ').trim();
async function metadata(title){
 const pieces=String(title).replace(/\s*\((official|lyrics?|video|audio|hd|4k).*?\)/ig,'').split(/\s+[-–—]\s+/);
 const artist=pieces.length>1?pieces.shift().trim():'',song=pieces.join(' - ').trim()||title;
 const m={artist,song,year:'Não confirmado',album:'Não confirmado',origin:'Não confirmado',cover:''};
 if(!artist)return m;
 try{
 const r=await fetch('https://itunes.apple.com/search?term='+encodeURIComponent(artist+' '+song)+'&entity=song&limit=20&country=BR',{signal:AbortSignal.timeout(4500)});
 if(r.ok){const data=await r.json();const hit=(data.results||[]).find(x=>norm(x.artistName)===norm(artist)&&norm(x.trackName)===norm(song));if(hit){m.artist=hit.artistName;m.song=hit.trackName;m.album=hit.collectionName||m.album;m.year=hit.releaseDate?.slice(0,4)||m.year;m.cover=hit.artworkUrl100?.replace('100x100bb','600x600bb')||'';}}
 }catch(e){console.warn('Metadata not found',e)}
 return m;
}
const fmt=t=>Number.isFinite(t)&&t>0?Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0'):'Não informado';
$('pdfPreview').onclick=async()=>{
 if(!analyzed?.segments?.length)return;
 const btn=$('pdfPreview');btn.disabled=true;btn.textContent='Preparando páginas A4...';
 try{
 let videoTitle=currentTitle||lastFile?.name||'Música sem título',channel='';
 if(currentVideoId)try{const r=await fetch('https://www.youtube.com/oembed?url='+encodeURIComponent('https://www.youtube.com/watch?v='+currentVideoId)+'&format=json',{signal:AbortSignal.timeout(4000)});if(r.ok){const j=await r.json();videoTitle=j.title||videoTitle;channel=j.author_name||''}}catch(e){}
 const m=await metadata(videoTitle);
 const song=m.song||videoTitle,artist=m.artist||channel||'Não identificado';
 const duration=analyzed.audio_duration||analyzed.duration||activeMedia?.duration||0;
 const thumb=currentVideoId?'https://i.ytimg.com/vi/'+encodeURIComponent(currentVideoId)+'/hqdefault.jpg':'';
 const include=$('pdfContent').value==='both';
 const rows=analyzed.segments.map(s=>'<article class="verse"><div class="original">'+esc(s.original)+'</div>'+(include?'<div class="translated">'+esc(s.translation||'Tradução indisponível')+'</div>':'')+'</article>').join('');
 const header='<header class="mast"><div class="brand">♫ MUSICSENSE AI · SONGBOOK</div><div class="hero"><div class="covers">'+(thumb?'<figure><img src="'+thumb+'"><figcaption>Videoclipe</figcaption></figure>':'')+(m.cover?'<figure><img src="'+esc(m.cover)+'"><figcaption>Capa do álbum</figcaption></figure>':'')+'</div><div><h1>'+esc(song)+'</h1><h2>'+esc(artist)+'</h2><div class="meta"><b>Duração:</b> '+fmt(duration)+' · <b>Ano de lançamento:</b> '+esc(m.year)+'<br><b>Álbum:</b> '+esc(m.album)+'<br><b>Origem do artista:</b> '+esc(m.origin)+'<br><b>Idioma original:</b> '+esc(analyzed.language||'não identificado')+(channel?'<br><b>Canal do vídeo:</b> '+esc(channel):'')+'</div></div></div><p class="note">Metadados exibidos apenas quando confirmados. Ano de lançamento não significa necessariamente ano do sucesso.</p></header>';
 const css='@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;background:#dfe2e9;font-family:Arial,sans-serif;color:#20263b}.toolbar{position:sticky;top:0;z-index:99;background:#17172d;color:white;padding:12px;display:flex;justify-content:center;align-items:center;gap:10px;flex-wrap:wrap}.toolbar button{background:#b99aff;border:0;border-radius:7px;padding:9px 15px;font-weight:700;cursor:pointer}.toolbar .zoom{min-width:44px;font-size:18px}.toolbar span{font-size:13px}.sheet-wrap{width:210mm;margin:16px auto;transform-origin:top center}.sheet{width:210mm;height:297mm;background:#fff;padding:15mm 14mm 13mm;box-shadow:0 3px 18px #0002;margin:0 0 18px;overflow:hidden;position:relative}.mast{border-bottom:2px solid #a991ff;padding-bottom:9mm;margin-bottom:6mm}.brand{color:#7652b4;font-size:10px;letter-spacing:2px;font-weight:700}.hero{display:flex;gap:12px;margin-top:12px;align-items:center}.covers{display:flex;gap:7px;flex-shrink:0}.covers figure{margin:0;width:92px}.covers img{width:92px;height:78px;object-fit:cover;border-radius:6px}.covers figcaption{text-align:center;color:#777;font-size:9px}h1{font-size:21px;margin:0 0 4px;line-height:1.2}h2{font-size:15px;margin:0 0 8px;color:#635281}.meta{font-size:10px;line-height:1.65;color:#535b70}.note{font-size:8px;color:#7a8191;margin:9px 0 0}.columns{display:grid;grid-template-columns:1fr 1fr;gap:8mm}.column{min-width:0}.verse{border-bottom:1px solid #ecebf1;padding:6px 0 7px;break-inside:avoid}.original{font-size:11.5px;line-height:1.35;font-weight:700}.translated{font-size:10.5px;line-height:1.35;color:#71599c;margin-top:4px}.folio{position:absolute;bottom:7mm;left:14mm;right:14mm;display:flex;justify-content:space-between;color:#89909e;font-size:9px;border-top:1px solid #eee;padding-top:5px}@media print{html,body{background:white}.toolbar{display:none}.sheet-wrap{zoom:1!important;width:auto;margin:0}.sheet{box-shadow:none;margin:0;break-after:page;page-break-after:always}.sheet:last-child{break-after:auto;page-break-after:auto}}';
 const html='<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>'+esc(song)+' | MusicSense AI</title><style>'+css+'</style></head><body><nav class="toolbar"><span>Prévia A4 · páginas separadas</span><button class="zoom" id="minus">−</button><span id="pct">100%</span><button class="zoom" id="plus">+</button><button id="print">Imprimir / Salvar PDF</button><button id="close">Fechar</button></nav><main id="pages" class="sheet-wrap"></main><div id="source" style="display:none">'+rows+'</div><template id="head">'+header+'</template><script src="/songbook_pages_204.js"><\/script></body></html>';
 const w=window.open('','_blank');if(!w){setStatus('Permita pop-ups para visualizar o PDF.');return}
 w.document.open();w.document.write(html);w.document.close();$('pdfDialog').close();
 }catch(e){console.error(e);setStatus('Erro ao preparar PDF: '+e.message)}
 finally{btn.disabled=false;btn.textContent='Visualizar / Imprimir / Salvar PDF'}
};
})();