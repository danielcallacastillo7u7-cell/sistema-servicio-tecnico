(function iniciarOrdenes(eventoInicial) {
    if (document.readyState === 'loading' && eventoInicial?.type !== 'DOMContentLoaded') {
        document.addEventListener('DOMContentLoaded', iniciarOrdenes, { once: true });
        return;
    }
    const formulario = document.getElementById('ordenForm');
    if (!formulario || formulario.dataset.equiposInicializados === 'true') return;
    const contenedor = document.getElementById('equiposContenedor');
    const agregar = document.getElementById('agregarEquipo');
    const tecnico = document.getElementById('tecnicoResponsable');
    const clientes = [...document.querySelectorAll('#datosCliente input')];
    const plantilla = contenedor.firstElementChild.cloneNode(true);
    const estados = new WeakMap();
    let siguienteId = 0;
    let ocupado = false;
    const bloques = () => [...contenedor.children];

    function condiciones(bloque) {
        for (const [selector, valor, campo] of [
            ['tipo', 'Otro', 'tipo_otro'],
            ['accesorio_opcion', 'Especificar', 'accesorios_detalle'],
        ]) {
            const input = bloque.querySelector(`[name="${campo}"]`);
            const visible = bloque.querySelector(`[name="${selector}"]`).value === valor;
            input.closest('.conditional-field').hidden = !visible;
            input.required = visible;
        }
    }

    function actualizar() {
        const guardados = bloques().filter(b => estados.get(b).guardado).length;
        const incierto = bloques().some(b => estados.get(b).incierto);
        clientes.forEach(c => { c.readOnly = ocupado || guardados > 0 || incierto || (c.name !== 'dni_ruc' && (formulario.dataset.clienteRegistrado === 'true' || formulario.dataset.consultandoCliente === 'true')); });
        tecnico.disabled = ocupado || incierto;
        bloques().forEach((bloque, indice) => {
            const estado = estados.get(bloque);
            bloque.querySelector('.equipo-numero').textContent = `Equipo ${indice + 1}`;
            bloque.setAttribute('aria-label', `Equipo ${indice + 1}`);
            const quitar = bloque.querySelector('.quitar-equipo');
            quitar.hidden = indice === 0 || estado.guardado;
            quitar.disabled = ocupado || estado.incierto;
            quitar.setAttribute('aria-label', `Quitar Equipo ${indice + 1}`);
            const boton = bloque.querySelector('.guardar-equipo');
            boton.disabled = ocupado || estado.guardado || !tecnico.querySelector('option[value]:not([value=""])');
        });
        document.getElementById('cantidadEquipos').textContent = `${bloques().length} equipos · ${guardados} registrados · ${bloques().length - guardados} pendientes`;
    }

    function tokenSolicitud() {
        if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
        // HTTP por IP local: getRandomValues funciona sin contexto seguro.
        const bytes = crypto.getRandomValues(new Uint8Array(16));
        bytes[6] = (bytes[6] & 0x0f) | 0x40;
        bytes[8] = (bytes[8] & 0x3f) | 0x80;
        const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
        return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
    }

    function crear(datos = {}, reemplazar = false) {
        const bloque = plantilla.cloneNode(true);
        const id = ++siguienteId;
        bloque.querySelectorAll('[id]').forEach(e => e.removeAttribute('id'));
        bloque.querySelectorAll('input, select, textarea').forEach(campo => {
            campo.id = `equipo-${id}-${campo.name}`;
            campo.value = typeof datos[campo.name] === 'string' ? datos[campo.name] : '';
            campo.parentElement.querySelector('label')?.setAttribute('for', campo.id);
        });
        estados.set(bloque, { token: tokenSolicitud(), guardado: false, incierto: false, envio: null });
        condiciones(bloque);
        // Reemplaza el HTML inicial solo cuando el nuevo bloque está listo.
        if (reemplazar) contenedor.replaceChildren(bloque);
        else contenedor.appendChild(bloque);
        actualizar();
        return bloque;
    }

    function mostrarTicket(bloque, datos, imprimirAlCargar = false) {
        const detalle = bloque.querySelector('.equipo-ticket');
        const frame = detalle.querySelector('iframe');
        const imprimir = detalle.querySelector('.imprimir-equipo');
        detalle.hidden = false;
        detalle.open = true;
        detalle.querySelector('summary').textContent = `Ticket ${datos.numero_orden}`;
        frame.title = `Ticket ${datos.numero_orden}`;
        frame.hidden = false;
        frame.addEventListener('load', () => {
            // Un fallo al cargar la vista no debe permitir volver a guardar la orden.
            imprimir.disabled = !frame.contentDocument?.getElementById('ticketImprimible');
            if (!imprimir.disabled && imprimirAlCargar) {
                // El registro ya está confirmado y el ticket terminó de cargar.
                imprimirAlCargar = false;
                requestAnimationFrame(() => imprimir.click());
            }
        });
        frame.src = datos.ticket_url;
        imprimir.addEventListener('click', () => {
            frame.contentWindow.focus();
            frame.contentWindow.print();
        });
    }

    function agregarFila(bloque, datos) {
        const tabla = document.querySelector('#ordenesRegistradas tbody');
        if (!tabla) return;
        if (tabla.querySelector('td[colspan]')) tabla.replaceChildren();
        const fila = document.createElement('tr');
        const equipo = nombre => bloque.querySelector(`[name="${nombre}"]`).value;
        for (const texto of [datos.numero_orden, `${clientes[0].value} ${clientes[1].value} · ${equipo('tipo')} ${equipo('marca')} ${equipo('modelo')}`, datos.estado]) {
            const celda = document.createElement('td');
            celda.textContent = texto;
            fila.appendChild(celda);
        }
        const celda = document.createElement('td');
        const boton = document.createElement('button');
        boton.type = 'button';
        boton.className = 'btn btn-sm btn-outline-dark';
        boton.textContent = 'Ver ticket';
        boton.addEventListener('click', () => {
            if (!bloque.isConnected) {
                if (!celda.querySelector('.equipo-ticket')) {
                    celda.appendChild(plantilla.querySelector('.equipo-ticket').cloneNode(true));
                    mostrarTicket(celda, datos);
                } else {
                    celda.querySelector('.equipo-ticket').open = true;
                }
                return;
            }
            bloque.querySelector('.equipo-ticket').open = true;
            bloque.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
        celda.appendChild(boton);
        fila.appendChild(celda);
        tabla.prepend(fila);
    }

    async function guardar(bloque) {
        const estado = estados.get(bloque);
        if (ocupado || estado.guardado) return;
        if (!estado.envio && formulario.verificarCliente) {
            if (!await formulario.verificarCliente()) return;
            if (ocupado || estado.guardado) return;
        }
        const campos = [...bloque.querySelectorAll('input, select, textarea')];
        if (!estado.envio) {
            // Validar solamente al cliente y al equipo cuyo botón se pulsó.
            for (const campo of [...clientes, tecnico, ...campos]) {
                if (!campo.reportValidity()) return;
            }
            const datos = new URLSearchParams();
            [...clientes, tecnico, ...campos].forEach(c => datos.set(c.name, c.value));
            datos.set('solicitud_token', estado.token);
            estado.envio = datos.toString();
        }
        ocupado = true;
        const boton = bloque.querySelector('.guardar-equipo');
        const mensaje = bloque.querySelector('.equipo-error');
        const etiqueta = bloque.querySelector('.equipo-estado');
        mensaje.hidden = true;
        boton.textContent = 'Guardando…';
        etiqueta.textContent = 'Generando ticket…';
        campos.forEach(c => { c.disabled = true; });
        actualizar();
        const controlador = new AbortController();
        const espera = setTimeout(() => controlador.abort(), 20000);
        try {
            const respuesta = await fetch('/ordenes/guardar-equipo', {
                method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json' },
                body: estado.envio, signal: controlador.signal,
            });
            const datos = await respuesta.json();
            if (!respuesta.ok) {
                if (respuesta.status >= 500) throw new Error('Respuesta incierta');
                estado.envio = null;
                estado.incierto = false;
                campos.forEach(c => { c.disabled = false; });
                condiciones(bloque);
                mensaje.textContent = typeof datos.detail === 'string' ? datos.detail : 'Revisa los datos de este equipo.';
                mensaje.hidden = false;
                boton.textContent = 'Guardar y generar ticket';
                etiqueta.textContent = 'Pendiente de guardar';
                return;
            }
            if (!datos.id || !datos.numero_orden || !datos.ticket_url) throw new Error('Respuesta incompleta');
            estado.guardado = true;
            estado.incierto = false;
            bloque.dataset.guardado = 'true';
            boton.textContent = 'Registrado';
            etiqueta.textContent = `✓ Ticket listo · ${datos.numero_orden}`;
            mostrarTicket(bloque, datos, true);
            agregarFila(bloque, datos);
        } catch (_) {
            if (!estado.guardado) {
                estado.incierto = true;
                mensaje.textContent = 'No se pudo confirmar la respuesta. Pulsa «Comprobar guardado»; se recuperará el mismo ticket sin duplicar la orden.';
                mensaje.hidden = false;
                boton.textContent = 'Comprobar guardado';
                etiqueta.textContent = 'Confirmación pendiente';
            }
        } finally {
            clearTimeout(espera);
            ocupado = false;
            actualizar();
        }
    }

    // Solo se recuperan datos devueltos por el servidor tras una validación.
    // No se lee localStorage ni sessionStorage para construir el formulario.
    let previo = {};
    try {
        const datos = JSON.parse(document.getElementById('formularioPrevio')?.textContent || '{}');
        if (datos && typeof datos === 'object' && !Array.isArray(datos)) previo = datos;
    } catch (_) { /* Iniciar con un equipo vacío si los datos no son válidos. */ }
    formulario.reset();
    delete formulario.dataset.clienteRegistrado;
    delete formulario.dataset.consultandoCliente;
    clientes.forEach(c => { c.value = typeof previo[c.name] === 'string' ? previo[c.name] : ''; });
    tecnico.value = typeof previo.tecnico_responsable === 'string' ? previo.tecnico_responsable : '';
    let equipos = [previo];
    if (previo.equipos_json) {
        try {
            const datos = JSON.parse(previo.equipos_json);
            if (Array.isArray(datos) && datos.length && datos.every(e => e && typeof e === 'object' && !Array.isArray(e))) {
                equipos = datos.map(e => ({ ...e, falla_reportada: previo.falla_reportada || '', tecnico_responsable: previo.tecnico_responsable || '' }));
            }
        } catch (_) { /* La página ya muestra el error del envío anterior. */ }
    }
    equipos.forEach((datos, indice) => crear(datos, indice === 0));
    formulario.dataset.equiposInicializados = 'true';
    // Volver desde la caché de navegación debe obtener una vista nueva.
    window.addEventListener('pageshow', evento => {
        if (evento.persisted) window.location.replace('/ordenes');
    });
    agregar.addEventListener('click', () => crear().querySelector('select').focus());
    contenedor.addEventListener('change', evento => condiciones(evento.target.closest('.equipo-bloque')));
    contenedor.addEventListener('click', evento => {
        const guardarBoton = evento.target.closest('.guardar-equipo');
        if (guardarBoton) { guardar(guardarBoton.closest('.equipo-bloque')); return; }
        const quitar = evento.target.closest('.quitar-equipo');
        if (!quitar || quitar.hidden || quitar.disabled) return;
        quitar.closest('.equipo-bloque').remove();
        actualizar();
        agregar.focus();
    });
    formulario.addEventListener('cliente-consultado', actualizar);
    formulario.addEventListener('submit', evento => evento.preventDefault());
})();
