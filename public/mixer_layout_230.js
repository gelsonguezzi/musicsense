/* MusicSense 230: studio desk layout; reuses LIVE player/export controls. */
(function(){
'use strict';
function element(tag,className,text){
 const node=document.createElement(tag);
 if(className)node.className=className;
 if(text!==undefined)node.textContent=text;
 return node;
}
function section(className,title,subtitle){
 const card=element('section','ms230-card '+className);
 const header=element('div','ms230-card-head');
 header.append(element('h3','',title));
 if(subtitle)header.append(element('p','',subtitle));
 card.append(header);
 return card;
}
function mount({dialog,title,help,hint,noteEl,controls,seek,clock,area}){
 if(dialog.classList.contains('ms230'))return;
 dialog.classList.add('ms230');
 // The original elements retain their event handlers and accessible names.
 const root=element('div','ms230-layout');
 const header=element('header','ms230-header');
 const heading=element('div','ms230-heading');
 const kicker=element('span','ms230-kicker','MUSICSENSE  ·  ESTÚDIO');
 const displayTitle=element('h2','ms230-title','Mesa de instrumentos');
 const shortDescription=element('p','ms230-subtitle','Crie sua mixagem e prepare um karaokê com apoios vocais.');
 heading.append(kicker,displayTitle,shortDescription);
 const badge=element('span','ms230-track-count','6 trilhas');
 badge.setAttribute('aria-label','Quantidade de canais de áudio disponíveis');
 const exit=controls.querySelector('button:nth-child(3)');
 exit.classList.add('ms230-close');
 exit.setAttribute('aria-label','Fechar mesa de instrumentos');
 exit.textContent='✕ Fechar';
 header.append(heading,badge,exit);
 root.append(header);
 // Keep title in DOM, so the existing vocal updater still writes into it.
 title.classList.add('ms230-original-title');
 const observer=new MutationObserver(()=>{
   const n=title.textContent.match(/(\d+)\s+trilhas?/);
   if(n)badge.textContent=n[1]+' trilhas';
 });
 observer.observe(title,{childList:true,characterData:true,subtree:true});
 const number=title.textContent.match(/(\d+)\s+trilhas?/);
 if(number)badge.textContent=number[1]+' trilhas';
 title.hidden=true;
 help.hidden=true;
 hint.hidden=true;
 root.append(title,help,hint);
 // Status contains the live vocal progress inserted after noteEl.
 const status=section('ms230-status','Karaokê inteligente');
 const statusContent=element('div','ms230-status-content');
 const liveDot=element('span','ms230-live-dot');
 const statusText=element('div','ms230-status-copy');
 statusText.append(element('strong','', 'Voz principal e apoios vocais'));
 noteEl.classList.add('ms230-status-note');
 statusText.append(noteEl);
 statusContent.append(liveDot,statusText);
 status.append(statusContent);
 root.append(status);
 // Playback and export cards in parallel desktop columns.
 const upper=element('div','ms230-top-grid');
 const playback=section('ms230-playback','Reprodução','Ouça sua mixagem e navegue pela música.');
 const playRow=element('div','ms230-play-actions');
 const play=controls.querySelector('button:nth-child(1)');
 const stop=controls.querySelector('button:nth-child(2)');
 play.classList.add('ms230-play');
 stop.classList.add('ms230-stop');
 playRow.append(play,stop);
 const timeline=element('div','ms230-timeline');
 const timeLabel=element('span','ms230-time-label','POSIÇÃO');
 clock.classList.add('ms230-clock');
 const times=element('div','ms230-time-row');
 times.append(timeLabel,clock);
 seek.classList.add('ms230-seek');seek.style.width='';
 timeline.append(times,seek);
 playback.append(playRow,timeline);
 const exportCard=section('ms230-export','Salvar e compartilhar','Baixe as trilhas escolhidas ou o videoclipe legendado.');
 const actionRow=element('div','ms230-export-actions');
 const zip=[...controls.querySelectorAll('button')].find(x=>x.textContent.includes('multitrilhas'));
 const mp4=[...controls.querySelectorAll('button')].find(x=>x.textContent.includes('MP4'));
 if(zip){zip.classList.add('ms230-zip');actionRow.append(zip)}
 if(mp4){mp4.classList.add('ms230-mp4');actionRow.append(mp4)}
 exportCard.append(actionRow);
 const options=dialog.querySelector('.ms227-options');
 if(options){options.classList.add('ms230-form');exportCard.append(options)}
 const exportProgress=dialog.querySelector('.ms227-job');
 if(exportProgress)exportCard.append(exportProgress);
 upper.append(playback,exportCard);root.append(upper);
 // Voice FX retain existing checkbox callbacks and current state.
 const fx=section('ms230-effects','Efeitos da voz','Ative somente quando desejar acrescentar efeitos à voz.');
 const voiceBox=dialog.querySelector('.ms227-fx');
 if(voiceBox){voiceBox.classList.add('ms230-fx-row');fx.append(voiceBox)}
 root.append(fx);
 // Instruments get their own large studio surface with original live grid.
 const instruments=section('ms230-instruments','Canais de áudio','Toque no instrumento para ativá-lo. M silencia; S isola a trilha e a seleciona para exportação.');
 const countText=element('span','ms230-track-helper','Trilhas sincronizadas');
 instruments.querySelector('.ms230-card-head').append(countText);
 instruments.append(area);
 root.append(instruments);
 const footer=element('footer','ms230-footer');
 const info=dialog.querySelector('.ms227-help');
 if(info){info.classList.add('ms230-footer-copy');footer.append(info)}
 else footer.append(element('p','','Marque S nos instrumentos que deseja incluir no arquivo exportado.'));
 root.append(footer);
 // Keep legacy container, but do not let it introduce empty spacing.
 controls.classList.add('ms230-empty-controls');
 dialog.replaceChildren(root,controls);
 const onVocal=()=>{if(!dialog.isConnected)observer.disconnect()};
 dialog.addEventListener('close',()=>observer.disconnect(),{once:true});
 // Basic click targets remain native buttons; no duplicate event listeners.
}
window.MusicSenseLayout230={mount};
})();