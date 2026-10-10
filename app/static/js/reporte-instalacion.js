(() => {
 let dialog,frame,download,opener,overflow,printButton;
 function open(url){
  const target=new URL(url,location.origin);if(target.origin!==location.origin)return;
  let title='Reporte de instalación',pdf=target.pathname+'.pdf';
  const order=target.pathname.match(/^\/ordenes\/(\d+)\/ticket$/);
  const payment=target.pathname.match(/^\/pagos-internet\/(\d+)\/ticket$/);
  if(order){title='Reporte de la orden';pdf=target.pathname+'.pdf';}
  else if(payment){title='Comprobante de pago de internet';pdf=target.pathname.replace(/ticket$/, 'pdf');target.searchParams.set('embed','1');}
  else if(!/^\/camaras\/\d+\/reporte$/.test(target.pathname))return;

  if(!dialog){dialog=document.createElement('dialog');dialog.className='installation-dialog';dialog.setAttribute('aria-labelledby','installation-dialog-title');dialog.innerHTML='<header><h2 id="installation-dialog-title">Reporte de instalación</h2><button type="button" aria-label="Cerrar reporte">×</button></header><iframe title="Detalle del reporte de instalación"></iframe><footer><button type="button" class="btn btn-outline-primary" data-print-report disabled>Imprimir ticket</button><a class="btn btn-primary" download>Descargar PDF</a><button type="button" class="btn btn-outline-secondary">Cerrar</button></footer>';document.body.append(dialog);frame=dialog.querySelector('iframe');download=dialog.querySelector('a');printButton=dialog.querySelector('[data-print-report]');frame.addEventListener('load',()=>{printButton.disabled=!frame.contentDocument?.querySelector('.ticket, #ticketImprimible')&&!frame.contentDocument?.title;});printButton.addEventListener('click',()=>{frame.contentWindow.focus();frame.contentWindow.print();});dialog.querySelectorAll('button:not([data-print-report])').forEach(b=>b.onclick=()=>dialog.close());dialog.addEventListener('close',()=>{document.body.style.overflow=overflow;frame.src='about:blank';opener?.focus();});dialog.addEventListener('click',e=>{if(e.target===dialog){const b=dialog.getBoundingClientRect();if(e.clientX<b.left||e.clientX>b.right||e.clientY<b.top||e.clientY>b.bottom)dialog.close();}});}
  opener=document.activeElement;dialog.querySelector('h2').textContent=title;frame.title=title;printButton.disabled=true;printButton.textContent=payment||order?'Imprimir ticket':'Imprimir reporte';frame.src=target.href;download.href=pdf;if(!dialog.open){overflow=document.body.style.overflow;dialog.showModal();}document.body.style.overflow='hidden';
 }
 window.ServiInstallationReport={open};
 document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||e.button!==0)return;const u=new URL(a.href,location.href);if(u.origin!==location.origin)return;
 if(u.pathname==='/ordenes'&&/^\d+$/.test(u.searchParams.get('ticket')||'')){u.pathname='/ordenes/'+u.searchParams.get('ticket')+'/ticket';u.search='';}
 if(/^\/(?:camaras\/\d+\/reporte|ordenes\/\d+\/ticket|pagos-internet\/\d+\/ticket)$/.test(u.pathname)){e.preventDefault();e.stopImmediatePropagation();open(u.href);}
 },true);
})();
