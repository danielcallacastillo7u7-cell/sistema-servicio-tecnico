(() => {
 let dialog,frame,download,opener;
 function open(url){
  if(!dialog){dialog=document.createElement('dialog');dialog.className='installation-dialog';dialog.setAttribute('aria-labelledby','installation-dialog-title');dialog.innerHTML='<header><h2 id="installation-dialog-title">Reporte de instalación</h2><button type="button" aria-label="Cerrar reporte">×</button></header><iframe title="Detalle del reporte de instalación"></iframe><footer><a class="btn btn-primary" download>Descargar PDF</a><button type="button" class="btn btn-outline-secondary">Cerrar</button></footer>';document.body.append(dialog);frame=dialog.querySelector('iframe');download=dialog.querySelector('a');dialog.querySelectorAll('button').forEach(b=>b.onclick=()=>dialog.close());dialog.addEventListener('close',()=>{document.body.style.overflow='';frame.src='about:blank';opener?.focus();});dialog.addEventListener('click',e=>{if(e.target===dialog){const b=dialog.getBoundingClientRect();if(e.clientX<b.left||e.clientX>b.right||e.clientY<b.top||e.clientY>b.bottom)dialog.close();}});}
  opener=document.activeElement;frame.src=url;download.href=url+'.pdf';if(!dialog.open)dialog.showModal();document.body.style.overflow='hidden';
 }
 window.ServiInstallationReport={open};
 document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||e.button!==0)return;const u=new URL(a.href,location.href);if(u.origin===location.origin&&/^\/camaras\/\d+\/reporte$/.test(u.pathname)){e.preventDefault();open(u.pathname);}});
})();