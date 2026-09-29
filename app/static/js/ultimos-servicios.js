(() => {
 const tabs = [...document.querySelectorAll('[data-servicio]')];
 const urls = {ordenes:'/?estado=Todas', instalaciones:'/camaras/reportes', pagos:'/pagos-internet'};
 function select(tab) {
   tabs.forEach(t => {const active=t===tab;t.setAttribute('aria-selected',String(active));t.tabIndex=active?0:-1;document.getElementById(t.getAttribute('aria-controls')).hidden=!active;});
   document.getElementById('serviciosVerTodos').href=urls[tab.dataset.servicio];
 }
 tabs.forEach((tab,index) => {
   tab.addEventListener('click',()=>select(tab));
   tab.addEventListener('keydown',e=>{
     let next;
     if(e.key==='ArrowRight')next=(index+1)%tabs.length;
     else if(e.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;
     else if(e.key==='Home')next=0;
     else if(e.key==='End')next=tabs.length-1;
     else return;
     e.preventDefault();select(tabs[next]);tabs[next].focus();
   });
 });
})();