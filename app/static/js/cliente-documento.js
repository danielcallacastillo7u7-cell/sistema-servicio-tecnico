(() => {
    const form = document.getElementById('ordenForm');
    if (!form) return;
    const documento = form.querySelector('[name="dni_ruc"]');
    const campos = ['nombres', 'apellidos', 'telefono'].map(n => form.querySelector(`[name="${n}"]`));
    const aviso = document.getElementById('documentoEstado');
    let version = 0, temporizador, pendiente, consultado = '', encontrado = false;
    const avisar = () => form.dispatchEvent(new Event('cliente-consultado'));

    async function consultar() {
        clearTimeout(temporizador);
        const valor = documento.value.trim();
        if (!/^(?:[0-9]{8}|[0-9]{11})$/.test(valor)) {
            aviso.textContent = 'Ingresa un DNI de 8 dígitos o un RUC de 11.';
            documento.reportValidity();
            return false;
        }
        if (consultado === valor) return true;
        if (pendiente?.documento === valor) return pendiente.promesa;
        const actual = ++version;
        form.dataset.consultandoCliente = 'true';
        aviso.textContent = 'Buscando cliente…';
        avisar();
        const controlador = new AbortController();
        const timeout = setTimeout(() => controlador.abort(), 10000);
        const promesa = (async () => {
            try {
                const respuesta = await fetch(`/clientes/por-documento/${encodeURIComponent(valor)}`, {signal: controlador.signal, cache: 'no-store'});
                if (!respuesta.ok) throw new Error('Consulta fallida');
                const datos = await respuesta.json();
                if (actual !== version || documento.value.trim() !== valor) return false;
                if (typeof datos.encontrado !== 'boolean') throw new Error('Respuesta inválida');
                consultado = valor;
                encontrado = datos.encontrado;
                form.dataset.clienteRegistrado = String(encontrado);
                if (encontrado) {
                    campos.forEach(c => { c.value = datos[c.name]; });
                    aviso.textContent = 'Cliente encontrado. Se usarán sus datos registrados, sin modificarlos.';
                } else {
                    aviso.textContent = 'DNI/RUC nuevo. Completa los datos para registrar al cliente.';
                }
                return true;
            } catch (_) {
                if (actual === version) aviso.textContent = 'No se pudo consultar el DNI/RUC. Vuelve a intentar antes de guardar.';
                return false;
            } finally {
                clearTimeout(timeout);
                if (actual === version) {
                    pendiente = null;
                    form.dataset.consultandoCliente = 'false';
                    avisar();
                }
            }
        })();
        pendiente = { documento: valor, promesa };
        return promesa;
    }

    documento.addEventListener('input', () => {
        ++version;
        clearTimeout(temporizador);
        pendiente = null;
        consultado = '';
        if (encontrado) campos.forEach(c => { c.value = ''; });
        encontrado = false;
        form.dataset.clienteRegistrado = 'false';
        form.dataset.consultandoCliente = 'false';
        aviso.textContent = 'Ingresa el DNI o RUC para buscar al cliente.';
        avisar();
        if (/^(?:[0-9]{8}|[0-9]{11})$/.test(documento.value.trim())) temporizador = setTimeout(consultar, 300);
    });
    documento.addEventListener('blur', () => { if (documento.value) consultar(); });
    form.verificarCliente = consultar;
})();
