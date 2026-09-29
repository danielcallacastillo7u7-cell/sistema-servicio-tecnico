(() => {
const el=id=>document.getElementById(id),fecha=el('inst-fecha');if(!fecha)return;
let mes=new Date((fecha.value||fecha.min)+'T12:00:00'),reservas=[],version=0;
const iso=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
function detalle(){el('agendaReservas').replaceChildren();const filas=reservas.filter(r=>r.fecha===fecha.value);filas.forEach(r=>{const li=document.createElement('li');li.textContent=`${r.hora} · ${r.tecnico} · ${r.numero}`;el('agendaReservas').append(li);});el('agendaEstado').textContent=fecha.value?(filas.length?`${filas.length} instalaciones en el día seleccionado.`:'No hay instalaciones reservadas en este día.'):'Selecciona un día para ver sus reservas.';}
function dibujar(){const grid=el('agendaDias');grid.replaceChildren();['L','M','X','J','V','S','D'].forEach(v=>{const s=document.createElement('span');s.textContent=v;grid.append(s);});const inicio=new Date(mes.getFullYear(),mes.getMonth(),1);for(let i=0;i<(inicio.getDay()+6)%7;i++)grid.append(document.createElement('span'));const max=new Date(mes.getFullYear(),mes.getMonth()+1,0).getDate();for(let i=1;i<=max;i++){const dia=iso(new Date(mes.getFullYear(),mes.getMonth(),i)),cantidad=reservas.filter(r=>r.fecha===dia).length,b=document.createElement('button');b.type='button';b.textContent=String(i);b.className='agenda-dia'+(cantidad?' reservado':'')+(dia===fecha.value?' seleccionado':'');b.disabled=dia<fecha.min;b.setAttribute('aria-label',`${dia}, ${cantidad} reservas`);b.setAttribute('aria-pressed',String(dia===fecha.value));b.onclick=()=>{fecha.value=dia;fecha.dispatchEvent(new Event('change',{bubbles:true}));cerrar();};grid.append(b);}detalle();}
async function cargar(){const v=++version;el('agendaMes').textContent=mes.toLocaleDateString('es-PE',{month:'long',year:'numeric'});el('agendaDias').replaceChildren();el('agendaReservas').replaceChildren();el('agendaEstado').textContent='Consultando reservas…';try{const r=await fetch(`/camaras/agenda?mes=${iso(new Date(mes.getFullYear(),mes.getMonth(),1))}`,{cache:'no-store'});if(!r.ok)throw Error();const d=await r.json();if(v!==version)return;reservas=d;dibujar();}catch(e){if(v===version)el('agendaEstado').textContent='No se pudieron consultar las reservas. Cierra y abre el calendario para reintentar.';}}
function cerrar(){el('installationAgenda').hidden=true;el('agendaAbrir').setAttribute('aria-expanded','false');el('agendaAbrir').focus();}
function abrir(){if(fecha.disabled)return;mes=new Date((fecha.value||fecha.min)+'T12:00:00');el('installationAgenda').hidden=false;el('agendaAbrir').setAttribute('aria-expanded','true');cargar();el('agendaNext').focus();}
el('agendaAbrir').onclick=()=>el('installationAgenda').hidden?abrir():cerrar();
el('agendaCerrar').onclick=cerrar;
el('agendaPrev').onclick=()=>{mes=new Date(mes.getFullYear(),mes.getMonth()-1,1);cargar();};
el('agendaNext').onclick=()=>{mes=new Date(mes.getFullYear(),mes.getMonth()+1,1);cargar();};
fecha.addEventListener('change',()=>{el('agendaFechaTexto').textContent=fecha.value?fecha.value.split('-').reverse().join('/'):'dd/mm/aaaa';});
fecha.addEventListener('invalid',e=>{e.preventDefault();abrir();});
document.addEventListener('pointerdown',e=>{if(!el('installationAgenda').hidden&&!e.target.closest('.agenda-field'))cerrar();});
el('installationAgenda').addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();cerrar();}});
})();
