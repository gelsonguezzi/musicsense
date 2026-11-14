(function(){
const pages=document.getElementById('pages'),src=document.getElementById('source');
const verses=[...src.children].map(n=>n.cloneNode(true));
let count=0,left,right,sheet,header;
function newPage(){
 count++;sheet=document.createElement('section');sheet.className='sheet';
 const head=count===1?document.getElementById('head').innerHTML:'<div class="brand" style="margin-bottom:8mm">♫ MUSICSENSE AI · SONGBOOK (continuação)</div>';
 sheet.innerHTML=head+'<div class="columns"><div class="column"></div><div class="column"></div></div><footer class="folio"><span>MusicSense AI · Transcrição e tradução automáticas</span><span>Página '+count+'</span></footer>';
 pages.append(sheet);[left,right]=sheet.querySelectorAll('.column');header=sheet.querySelector('.mast')||sheet.querySelector('.brand');
}
newPage();
function available(){
 return sheet.clientHeight-parseFloat(getComputedStyle(sheet).paddingTop)-parseFloat(getComputedStyle(sheet).paddingBottom)-sheet.querySelector('.folio').offsetHeight-18-header.offsetHeight-(count===1?20:12);
}
let current=left;
for(const verse of verses){
 current.append(verse);
 if(current.scrollHeight>available()){
 current.removeChild(verse);
 if(current===left){current=right;current.append(verse)}
 else{newPage();current=left;current.append(verse)}
 }
}
src.remove();
let zoom=100;
function setZoom(v){zoom=Math.max(50,Math.min(175,v));pages.style.zoom=zoom+'%';document.getElementById('pct').textContent=zoom+'%'}
document.getElementById('plus').onclick=()=>setZoom(zoom+10);
document.getElementById('minus').onclick=()=>setZoom(zoom-10);
document.getElementById('print').onclick=()=>window.print();
document.getElementById('close').onclick=()=>window.close();
})();