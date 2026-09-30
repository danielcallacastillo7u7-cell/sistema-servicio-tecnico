(() => {
 const button=document.querySelector('.sidebar .brand-logo');
 const nav=document.getElementById('appNavigation');
 if(!button||!nav)return;
 const small=window.matchMedia('(max-width:1000px)');
 const drawer=document.createElement('dialog');
 drawer.className='mobile-nav-drawer';
 drawer.setAttribute('aria-label','Menú principal');
 const header=document.createElement('div');header.className='mobile-nav-header';
 const title=document.createElement('strong');title.textContent='Menú principal';
 const close=document.createElement('button');close.type='button';close.className='mobile-nav-close';close.textContent='×';close.setAttribute('aria-label','Cerrar menú');
 header.append(title,close);drawer.append(header);document.body.append(drawer);
 const home=nav.parentNode;const next=nav.nextSibling;
 let oldOverflow='';
 function shut(){if(drawer.open)drawer.close();}
 drawer.addEventListener('close',()=>{document.body.style.overflow=oldOverflow;if(small.matches){button.setAttribute('aria-expanded','false');button.focus();}});
 close.addEventListener('click',shut);
 drawer.addEventListener('click',e=>{const b=drawer.getBoundingClientRect();if(e.target===drawer&&(e.clientX>b.right||e.clientX<b.left||e.clientY<b.top||e.clientY>b.bottom))shut();});
 button.addEventListener('click',event=>{
   if(!small.matches)return;
   event.preventDefault();
   if(drawer.open){shut();return;}
   oldOverflow=document.body.style.overflow;document.body.style.overflow='hidden';drawer.showModal();button.setAttribute('aria-expanded','true');
 });
 button.addEventListener('keydown',event=>{if(small.matches&&event.key===' '){event.preventDefault();button.click();}});
 nav.addEventListener('click',e=>{if(e.target.closest('a'))shut();});
 function sync(){
   shut();nav.hidden=false;
   if(small.matches){drawer.append(nav);button.setAttribute('role','button');button.setAttribute('aria-label','Abrir menú de ServiTech');button.setAttribute('aria-controls','appNavigation');button.setAttribute('aria-expanded','false');}
   else{home.insertBefore(nav,next);['role','aria-label','aria-controls','aria-expanded'].forEach(a=>button.removeAttribute(a));}
 }
 small.addEventListener('change',sync);sync();
})();
