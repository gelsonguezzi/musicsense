(function(){
 const button=document.getElementById('vocalSplit');
 if(!button)return;
 button.onclick=async()=>{
  const songId=(typeof currentVideoId!=='undefined'&&currentVideoId)||(typeof ytId!=='undefined'&&ytId);
  if(!songId){setStatus('Carregue uma musica do YouTube antes de separar a voz.');return}
  if(typeof analyzed==='undefined'||!analyzed){setStatus('Aguarde a analise da musica antes de separar a voz.');return}
  const original=button.innerHTML;button.disabled=true;
  try{
   button.innerHTML='<span>⏳ Separando voz...</span>';
   const r=await fetch('/api/separate-vocals',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:'https://www.youtube.com/watch?v='+songId})});
   const raw=await r.text();if(!raw.trim())throw Error('Servidor nao respondeu');
   const data=JSON.parse(raw);if(!r.ok)throw Error(data.error||'Erro');
   let result;
   for(let i=0;i<1800;i++){
    await new Promise(resolve=>setTimeout(resolve,1000));
    const x=await fetch('/api/export-progress?id='+encodeURIComponent(data.job_id),{cache:'no-store'});
    const txt=await x.text();if(!txt.trim())throw Error('Conexao interrompida');
    const info=JSON.parse(txt);
    button.innerHTML='<span>⏳ '+(info.percent||0)+'% · '+(info.stage||'Processando')+'</span>';
    if(info.done){if(info.error)throw Error(info.error);result=info;break}
   }
   if(!result)throw Error('Tempo limite excedido');
   const dialog=document.createElement('dialog');dialog.className='modal';
   const title=document.createElement('h2');title.textContent='Separacao concluida';
   dialog.append(title);
   const modeLabel=document.createElement('label');modeLabel.textContent='Letras no arquivo: ';modeLabel.style.cssText='display:block;margin:16px 0 8px';
   const mode=document.createElement('select');mode.style.cssText='width:100%;padding:10px;margin-top:6px';
   for(const [v,label] of [['none','Sem letras (MP3)'],['original','Somente transcricao (MP4)'],['translation','Somente traducao (MP4)'],['both','Transcricao + traducao (MP4)']]){
    const opt=document.createElement('option');opt.value=v;opt.textContent=label;mode.append(opt);
   }
   modeLabel.append(mode);dialog.append(modeLabel);
   const progress=document.createElement('div');progress.style.cssText='margin:12px 0;font-size:13px';dialog.append(progress);
   for(const [key,label] of [['instrumental','Instrumental (sem voz)'],['vocals','Voz isolada']]){
    const action=document.createElement('button');action.type='button';action.textContent='Baixar '+label;action.className='btn primary';action.style.cssText='display:block;width:100%;margin:12px 0;text-align:center';
    action.onclick=async()=>{
      if(mode.value==='none'){const a=document.createElement('a');a.href=result[key];a.download='MusicSense_'+key+'.mp3';document.body.append(a);a.click();a.remove();return}
      if(!analyzed?.segments?.length){progress.textContent='Nao ha transcricao para este arquivo';return}
      action.disabled=true;progress.textContent='Preparando MP4...';
      try{
        const req=await fetch('/api/export-stem-karaoke',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stem:result[key],mode:mode.value,segments:analyzed.segments})});
        const body=await req.text();if(!body.trim())throw Error('Servidor nao respondeu');
        const data=JSON.parse(body);if(!req.ok)throw Error(data.error||'Falha ao iniciar');
        let done=false;
        for(let i=0;i<900;i++){
          await new Promise(r=>setTimeout(r,1000));
          const resp=await fetch('/api/export-progress?id='+encodeURIComponent(data.job_id),{cache:'no-store'});
          const txt=await resp.text();if(!txt.trim())throw Error('Resposta vazia');
          const state=JSON.parse(txt);
          progress.textContent=(state.percent||0)+'% · '+(state.stage||'Gerando video');
          if(state.done){
            if(state.error)throw Error(state.error);
            const a=document.createElement('a');a.href=state.video_url;a.download='MusicSense_'+key+'_'+mode.value+'.mp4';document.body.append(a);a.click();a.remove();
            progress.textContent='MP4 pronto!';done=true;break;
          }
        }
        if(!done)throw Error('Tempo de espera excedido');
      }catch(e){progress.textContent='Erro: '+e.message}
      finally{action.disabled=false}
    };
    dialog.append(action);
   }
   const close=document.createElement('button');close.textContent='Fechar';close.className='btn ghost';close.onclick=()=>{dialog.close();dialog.remove()};dialog.append(close);
   document.body.append(dialog);dialog.showModal();
   setStatus('Separacao concluida. Escolha a faixa para baixar.');
  }catch(e){setStatus('Erro ao separar voz: '+e.message)}
  finally{button.disabled=false;button.innerHTML=original}
 };
})();