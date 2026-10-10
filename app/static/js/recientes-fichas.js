(() => {
const dialog=document.getElementById('recentFicha'),body=document.getElementById('recentContenido');let origin,overflow;
function open(row){const template=document.getElementById(row.dataset.recentFicha);if(!template)return;origin=row;body.replaceChildren(template.content.cloneNode(true));overflow=document.body.style.overflow;document.body.style.overflow='hidden';dialog.showModal();dialog.scrollTop=0;}
document.querySelectorAll('[data-recent-ficha]').forEach(row=>{row.addEventListener('click',()=>open(row));row.addEventListener('keydown',e=>{if(e.target===row&&(e.key==='Enter'||e.key===' ')){e.preventDefault();open(row);}});});
dialog.addEventListener('click',e=>{if(e.target.closest('.ficha-close,[data-close-ficha]'))dialog.close();});
dialog.addEventListener('close',()=>{document.body.style.overflow=overflow;origin?.focus();});
})();
