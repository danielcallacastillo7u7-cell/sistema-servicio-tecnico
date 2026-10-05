(() => {
const modal=document.getElementById('todasOrdenes');if(!modal)return;
const list=document.getElementById('allList'),cards=[...list.querySelectorAll('.all-order')];
const search=document.getElementById('allSearch'),state=document.getElementById('allState'),sort=document.getElementById('allSort');
const prev=document.getElementById('allPrev'),next=document.getElementById('allNext');let page=0;const size=8;
const norm=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
cards.forEach(c=>{c.dataset.search=norm(c.querySelector('.all-copy').textContent);let age=Math.max(0,Math.floor((Date.now()-new Date(c.dataset.date).getTime())/86400000));c.querySelector('.all-age').textContent=age===0?'Hoy':age===1?'Hace 1 día':`Hace ${age} días`;});
function render(){const q=norm(search.value.trim());const found=cards.filter(c=>(!state.value||c.dataset.state===state.value)&&c.dataset.search.includes(q));found.sort((a,b)=>{const n=new Date(a.dataset.date)-new Date(b.dataset.date)||Number(a.dataset.id)-Number(b.dataset.id);return sort.value==='asc'?n:-n;});page=Math.min(page,Math.max(0,Math.ceil(found.length/size)-1));cards.forEach(c=>{c.hidden=true;c.querySelector('details').open=false;});found.slice(page*size,(page+1)*size).forEach(c=>{c.hidden=false;list.append(c);});document.getElementById('allEmpty').hidden=found.length>0;document.getElementById('allCount').textContent=`${found.length} órdenes${q||state.value?' encontradas':' en total'}`;document.getElementById('allRange').textContent=found.length?`Mostrando ${page*size+1} - ${Math.min((page+1)*size,found.length)} de ${found.length}`:'Mostrando 0';prev.disabled=page===0;next.disabled=(page+1)*size>=found.length;list.scrollTop=0;}
search.addEventListener('input',()=>{page=0;render();});[state,sort].forEach(e=>e.addEventListener('change',()=>{page=0;render();}));prev.onclick=()=>{page--;render();};next.onclick=()=>{page++;render();};modal.addEventListener('cancel',e=>{e.preventDefault();location.href='/';});modal.addEventListener('click',e=>{const r=modal.getBoundingClientRect();if(e.target===modal&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))location.href='/';});render();modal.showModal();document.body.style.overflow='hidden';
})();

(() => {
 const ficha=document.getElementById('ordenFicha'), contenido=document.getElementById('ordenFichaContenido');
 let origen;
 function abrir(card){origen=card;contenido.replaceChildren(document.getElementById('ficha-'+card.dataset.id).content.cloneNode(true));ficha.showModal();ficha.scrollTop=0;}
 document.querySelectorAll('.all-order').forEach(card=>{
  card.addEventListener('click',e=>{if(!e.target.closest('details,a,button')) abrir(card);});
  card.addEventListener('keydown',e=>{if(e.target===card&&(e.key==='Enter'||e.key===' ')){e.preventDefault();abrir(card);}});
 });
 ficha.addEventListener('click',e=>{if(e.target.closest('.ficha-close,[data-close-ficha]')) ficha.close();});
 ficha.addEventListener('close',()=>origen?.focus());
})();
