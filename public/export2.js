window.MusicSenseExport={start:async function(){
  if(!lastFile||!analyzed)return setStatus('Selecione e analise um arquivo local primeiro.');
  const b=$('exportVideo');b.disabled=true;
  const old=b.innerHTML;b.innerHTML='<span class="actionicon">⏳</span><span><strong>Exportando MP4...</strong><small>Aguarde a renderização</small></span>';
  try{
    const fd=new FormData();fd.append('file',lastFile);fd.append('segments',JSON.stringify(analyzed.segments));
    const r=await fetch('/api/export-video',{method:'POST',body:fd});
    const data=await r.json();if(!r.ok)throw Error(data.error||'Falha na exportação');
    const a=document.createElement('a');a.href=data.video_url;a.download='MusicSense_Feed_4x5.mp4';document.body.append(a);a.click();a.remove();
    setStatus('MP4 vertical 4:5 exportado. Verifique a pasta Downloads antes de compartilhar.');
  }catch(e){setStatus('Erro na exportação: '+e.message)}
  finally{b.disabled=false;b.innerHTML=old}
}};

[executed on device: ESCRITORIO (015f09d9-8ae6-4cef-a39b-c7592204d204)]
