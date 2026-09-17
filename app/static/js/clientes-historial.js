(() => {
    if (!document.getElementById('clientesApp')) return;
    const el = id => document.getElementById(id);
    const html = valor => String(valor ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const equipoTexto = e => `${e.tipo} ${e.marca} ${e.modelo} · ${e.serie}`;
    const tareas = {};
    let paginaClientes = 1, paginaHistorial = 1, clienteId = null, ultimoBoton;
    let timerClientes, timerHistorial;
    let ultimaPendiente = true;

    async function consultar(tipo, url, mostrar) {
        tareas[tipo]?.abort();
        const control = new AbortController();
        tareas[tipo] = control;
        const espera = setTimeout(() => control.abort(), 15000);
        el(tipo+'Mensaje').textContent = 'Cargando…';
        if (tipo === 'historial') el('historialCarga').textContent = 'Cargando historial…';
        el(tipo+'Reintentar').hidden = true;
        el(tipo+'Anterior').disabled = el(tipo+'Siguiente').disabled = true;
        try {
            const r = await fetch(url, {signal:control.signal, cache:'no-store'});
            if (!r.ok) throw new Error();
            const datos = await r.json();
            if (tareas[tipo] !== control) return;
            mostrar(datos);
            if (tipo === 'historial') el('historialCarga').textContent = '';
            el(tipo+'Pagina').textContent = `Página ${datos.pagina} de ${datos.paginas}`;
            el(tipo+'Anterior').disabled = datos.pagina <= 1;
            el(tipo+'Siguiente').disabled = datos.pagina >= datos.paginas;
        } catch (_) {
            if (tareas[tipo] !== control) return;
            el(tipo+'Mensaje').textContent = 'No se pudo cargar la información. Vuelve a intentar.';
            if (tipo === 'historial') el('historialCarga').textContent = 'No se pudo cargar el historial. Vuelve a intentar.';
            el(tipo+'Reintentar').hidden = false;
        } finally { clearTimeout(espera); }
    }

    function clientes() {
        el('clientesFilas').replaceChildren();
        return consultar('clientes', `/clientes/api?q=${encodeURIComponent(el('buscarClientes').value)}&pagina=${paginaClientes}`, datos => {
            paginaClientes = datos.pagina;
            el('clientesMensaje').textContent = datos.total === 1 ? '1 cliente encontrado' : `${datos.total} clientes encontrados`;
            el('clientesFilas').innerHTML = datos.clientes.length ? datos.clientes.map(c => `<tr>
                <td>${html(c.nombres)} ${html(c.apellidos)}</td><td>${html(c.dni_ruc)}</td><td>${html(c.telefono)}</td>
                <td>${html(c.total_reparaciones)}</td><td>${c.ultima_reparacion ? `${html(c.ultima_reparacion.numero)}<br><small>${html(c.ultima_reparacion.fecha)} · ${html(c.ultima_reparacion.estado)}</small>` : 'Sin reparaciones'}</td>
                <td><button class="btn btn-sm btn-outline-primary" type="button" data-cliente="${c.id}">Ver detalles</button></td>
            </tr>`).join('') : '<tr><td colspan="6">No hay clientes para esta búsqueda.</td></tr>';
        });
    }

    function detalleOrden(o) {
        const d = o.diagnostico;
        return `<article class="border rounded p-3 mb-3">
            <div class="d-flex justify-content-between flex-wrap gap-2"><strong>${html(o.numero)}</strong><span>${html(o.estado)} · ${html(o.fecha)}</span></div>
            <p class="mt-2 mb-2">${o.equipos.map(e => html(equipoTexto(e))).join('<br>')}</p>
            <p class="mb-2"><b>Falla reportada:</b> ${html(o.falla_reportada)}</p>
            <details><summary class="text-primary" style="cursor:pointer">Ver detalles del equipo y reparación</summary>
                ${o.equipos.map(e=>`<section class="border-bottom py-3"><strong>${html(equipoTexto(e))}</strong><p class="mb-1"><b>Accesorios recibidos:</b> ${html(e.accesorios)}</p><p class="mb-1"><b>Observaciones de recepción:</b> ${html(e.observaciones)}</p><button type="button" class="btn btn-sm btn-outline-secondary" data-equipo="${e.id}">Ver todas las atenciones de este equipo</button></section>`).join('')}
                <p class="mt-3"><b>Técnico:</b> ${html(o.tecnico)}</p>
                <h3 class="h6">Diagnóstico de la orden</h3>
                ${d ? `<p><b>Falla encontrada:</b> ${html(d.falla)}</p><p><b>Solución recomendada:</b> ${html(d.solucion)}</p><p><b>Repuestos:</b> ${html(d.repuestos)}</p><p><b>Costo estimado:</b> S/ ${html(d.costo)}</p>
                ${d.imagenes.length ? `<div class="d-flex flex-wrap gap-2">${d.imagenes.map(i=>`<a href="${html(i.url)}" target="_blank" rel="noopener"><img src="${html(i.url)}" alt="${html(i.nombre)}" loading="lazy" style="width:120px;height:100px;object-fit:cover"></a>`).join('')}</div>` : '<p class="text-secondary">Sin imágenes adjuntas.</p>'}` : '<p class="text-secondary">Pendiente de diagnóstico.</p>'}
                <h3 class="h6 mt-3">Historial de estados</h3><ul>${o.historial.map(h=>`<li>${html(h.fecha)} — ${html(h.estado)}</li>`).join('') || '<li>Sin cambios registrados.</li>'}</ul>
                <details class="mt-3" data-ticket="${html(o.ticket_url)}"><summary style="cursor:pointer">Ver ticket de esta atención</summary><iframe title="Ticket ${html(o.numero)}" class="ticket-iframe" style="margin-top:12px" hidden></iframe></details>
            </details>
        </article>`;
    }

    function historial(cargarEquipos=false) {
        if (clienteId === null) return;
        el('historialOrdenes').replaceChildren();
        const params = new URLSearchParams({q:el('buscarHistorial').value,pagina:String(paginaHistorial)});
        if (el('historialEquipo').value) params.set('equipo_id',el('historialEquipo').value);
        return consultar('historial',`/clientes/api/${clienteId}/historial?${params}`, datos=>{
            paginaHistorial=datos.pagina;
            el('historialTitulo').textContent=`Historial de ${datos.cliente.nombres} ${datos.cliente.apellidos}`;
            el('historialCliente').textContent=`DNI/RUC: ${datos.cliente.dni_ruc} · Teléfono: ${datos.cliente.telefono}`;
            el('historialResumen').textContent=`${datos.equipos.length} equipos registrados · ${datos.total_ordenes} atenciones en total`;
            if (ultimaPendiente) {
                el('ultimaReparacion').innerHTML=datos.ordenes.length ? detalleOrden(datos.ordenes[0]) : '<p class="text-secondary">Este cliente todavía no tiene reparaciones registradas.</p>';
                el('todasReparaciones').hidden=datos.total_ordenes === 0;
                el('resumenReparaciones').textContent=`Ver todas las reparaciones (${datos.total_ordenes})`;
                ultimaPendiente=false;
            }
            const seleccionEquipo = el('historialEquipo').value;
            el('historialEquipo').innerHTML='<option value="">Todos los equipos</option>'+datos.equipos.map(e=>`<option value="${e.id}">${html(equipoTexto(e))}</option>`).join('');
            el('historialEquipo').value=seleccionEquipo;
            el('historialMensaje').textContent=datos.total === 1 ? '1 atención encontrada' : `${datos.total} atenciones encontradas`;
            el('historialOrdenes').innerHTML=datos.ordenes.length ? datos.ordenes.map(detalleOrden).join('') : '<p class="text-secondary">No hay atenciones para esta búsqueda.</p>';
        });
    }

    function demorar(tipo, callback) {
        tareas[tipo]?.abort(); tareas[tipo]=null;
        el(tipo+'Anterior').disabled=el(tipo+'Siguiente').disabled=true;
        el(tipo+'Mensaje').textContent='Buscando…';
        return setTimeout(callback,250);
    }
    el('buscarClientes').addEventListener('input',()=>{clearTimeout(timerClientes);paginaClientes=1;timerClientes=demorar('clientes',clientes);});
    el('buscarHistorial').addEventListener('input',()=>{clearTimeout(timerHistorial);paginaHistorial=1;timerHistorial=demorar('historial',()=>historial());});
    el('historialEquipo').addEventListener('change',()=>{clearTimeout(timerHistorial);paginaHistorial=1;historial();});
    for (const [tipo,cargar] of [['clientes',clientes],['historial',()=>historial()]]) {
        for (const [boton,delta] of [['Anterior',-1],['Siguiente',1]]) el(tipo+boton).addEventListener('click',()=>{if(tipo==='clientes')paginaClientes+=delta;else paginaHistorial+=delta;cargar();});
        el(tipo+'Reintentar').addEventListener('click',()=>tipo==='historial'?historial(true):clientes());
    }
    el('clientesFilas').addEventListener('click',event=>{
        const b=event.target.closest('[data-cliente]');if(!b)return;
        ultimoBoton=b;clienteId=Number(b.dataset.cliente);paginaHistorial=1;
        ultimaPendiente=true;el('ultimaReparacion').replaceChildren();
        el('todasReparaciones').open=false;el('todasReparaciones').hidden=true;
        clearTimeout(timerHistorial);
        el('buscarHistorial').value='';el('historialEquipo').innerHTML='<option value="">Todos los equipos</option>';
        el('historialTitulo').textContent='Historial del cliente';el('historialCliente').textContent='';el('historialResumen').textContent='';
        el('clienteHistorial').hidden=false;historial(true);
        el('historialTitulo').focus();el('clienteHistorial').scrollIntoView({behavior:'smooth',block:'start'});
    });
    el('cerrarHistorial').addEventListener('click',()=>{clearTimeout(timerHistorial);tareas.historial?.abort();tareas.historial=null;clienteId=null;el('clienteHistorial').hidden=true;ultimoBoton?.focus();});
    el('clienteHistorial').addEventListener('click',event=>{
        const b=event.target.closest('[data-equipo]');if(!b)return;
        clearTimeout(timerHistorial);el('todasReparaciones').open=true;
        el('historialEquipo').value=b.dataset.equipo;paginaHistorial=1;el('buscarHistorial').value='';historial();
    });
    el('clienteHistorial').addEventListener('toggle',event=>{
        const details=event.target;if(!details.matches('details[data-ticket]')||!details.open)return;
        const frame=details.querySelector('iframe');if(!frame.getAttribute('src'))frame.src=details.dataset.ticket;frame.hidden=false;
    },true);
    clientes();
})();
