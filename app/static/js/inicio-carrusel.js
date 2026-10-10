(() => {
 const track=document.querySelector('.dashboard-carousel-track');
 if(!track)return;
 let timer=null;
 fetch('/static/images/inicio-carrusel/imagenes.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Sin imágenes');return r.json();}).then(async slides=>{
  if(!Array.isArray(slides))return;
  const loaded=await Promise.all(slides.map(slide=>new Promise(resolve=>{if(!slide||typeof slide.src!=='string'||!slide.src.startsWith('/static/images/'))return resolve(null);const img=new Image();img.alt=slide.alt||'ServiTech';img.onload=()=>resolve(img);img.onerror=()=>resolve(null);img.src=slide.src;})));
  const images=loaded.filter(Boolean);if(!images.length)return;
  track.replaceChildren(...images);if(images.length<2)return;
  const clone=images[0].cloneNode(true);clone.setAttribute('aria-hidden','true');track.append(clone);
  let index=0;
  function advance(){index++;track.style.transform=`translateX(-${index*100}%)`;}
  track.addEventListener('transitionend',e=>{if(e.target!==track||e.propertyName!=='transform')return;if(index===images.length){track.style.transition='none';index=0;track.style.transform='translateX(0)';void track.offsetWidth;track.style.transition='';}});
  function start(){if(timer===null)timer=setInterval(advance,5000);}
  document.addEventListener('visibilitychange',()=>{if(document.hidden){clearInterval(timer);timer=null;}else start();});
  if(!document.hidden)start();
 }).catch(()=>{});
})();
