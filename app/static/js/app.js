const buscador = document.querySelector("#buscadorGlobal");
const resultados = document.querySelector("#resultadosBusqueda");
let temporizador;
let ordenesEncontradas = new Map();

const escaparHtml = valor => String(valor ?? "").replace(/[&<>'"]/g, caracter => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
})[caracter]);

function abrirDetalleOrden(item) {
    const diagnostico = item.especificaciones
        ? `<div class="detail-list"><span><b>Falla encontrada:</b> ${escaparHtml(item.especificaciones.falla_encontrada)}</span><span><b>Solución:</b> ${escaparHtml(item.especificaciones.solucion)}</span><span><b>Repuestos:</b> ${escaparHtml(item.especificaciones.repuestos)}</span><span><b>Costo:</b> S/ ${escaparHtml(item.especificaciones.costo)}</span></div>`
        : '<p class="detail-pending">Pendiente de diagnóstico.</p>';
    const modal = document.createElement("div");
    modal.className = "order-detail-modal";
    modal.innerHTML = `<div class="order-detail-backdrop" data-close-detail></div><section class="order-detail-panel" role="dialog" aria-modal="true" aria-labelledby="detailTitle"><header class="order-detail-header"><div><small>DETALLE DE LA ORDEN</small><h2 id="detailTitle">${escaparHtml(item.numero)}</h2></div><button type="button" class="order-detail-close" data-close-detail aria-label="Cerrar">×</button></header><div class="order-detail-body"><section class="detail-section"><h3><i class="bi bi-person"></i> Datos del cliente</h3><div class="detail-list"><span><b>Nombre:</b> ${escaparHtml(item.datos_cliente.nombres)}</span><span><b>DNI/RUC:</b> ${escaparHtml(item.datos_cliente.documento)}</span><span><b>Celular:</b> ${escaparHtml(item.datos_cliente.telefono)}</span></div></section><section class="detail-section"><h3><i class="bi bi-pc-display"></i> Datos del equipo</h3><div class="detail-list"><span><b>Equipo:</b> ${escaparHtml(item.datos_equipo.tipo)}</span><span><b>Marca:</b> ${escaparHtml(item.datos_equipo.marca)}</span><span><b>Modelo:</b> ${escaparHtml(item.datos_equipo.modelo)}</span><span><b>Serie:</b> ${escaparHtml(item.datos_equipo.serie)}</span><span><b>Accesorios:</b> ${escaparHtml(item.datos_equipo.accesorios)}</span><span><b>Observaciones:</b> ${escaparHtml(item.datos_equipo.observaciones)}</span></div></section><section class="detail-section"><h3><i class="bi bi-file-earmark-text"></i> Datos de la orden</h3><div class="detail-list"><span><b>Fecha:</b> ${escaparHtml(item.fecha)}</span><span><b>Estado:</b> ${escaparHtml(item.estado)}</span><span><b>Técnico:</b> ${escaparHtml(item.datos_orden.tecnico)}</span><span><b>Falla reportada:</b> ${escaparHtml(item.datos_orden.falla_reportada)}</span></div></section><section class="detail-section detail-diagnosis"><h3><i class="bi bi-activity"></i> Especificaciones / diagnóstico</h3>${diagnostico}</section></div><footer class="order-detail-actions"><a class="btn btn-outline-dark" href="/ordenes?ticket=${encodeURIComponent(item.id)}">Ver ticket</a><button type="button" class="btn btn-primary" data-close-detail>Cerrar</button></footer></section>`;
    const cerrar = () => modal.remove();
    modal.querySelectorAll("[data-close-detail]").forEach(elemento => elemento.addEventListener("click", cerrar));
    document.body.appendChild(modal);
    modal.querySelector(".order-detail-close").focus();
}

if (buscador && resultados) {
    buscador.addEventListener("input", () => {
        clearTimeout(temporizador);
        const consulta = buscador.value.trim();
        if (consulta.length < 2) {
            resultados.innerHTML = "";
            return;
        }
        temporizador = setTimeout(async () => {
            const respuesta = await fetch(`/api/buscar?q=${encodeURIComponent(consulta)}`);
            const datos = await respuesta.json();
            ordenesEncontradas = new Map(datos.map(item => [String(item.id), item]));
            resultados.innerHTML = datos.length
                ? datos.map(item => `<div class="search-item detailed"><div><strong>${escaparHtml(item.numero)}</strong><small>${escaparHtml(item.estado)}</small></div><div><span>${escaparHtml(item.cliente)}</span><span>${escaparHtml(item.equipo)}</span></div><button type="button" class="btn btn-sm btn-outline-primary detail-button" data-order-detail="${escaparHtml(item.id)}"><i class="bi bi-eye"></i> Detalles</button></div>`).join("")
                : '<p class="text-secondary mb-0">No se encontraron órdenes.</p>';
        }, 250);
    });
    resultados.addEventListener("click", evento => {
        const boton = evento.target.closest("[data-order-detail]");
        if (!boton) return;
        const item = ordenesEncontradas.get(boton.dataset.orderDetail);
        if (item) abrirDetalleOrden(item);
    });
}

document.querySelectorAll(".solo-letras").forEach(campo => {
    campo.addEventListener("input", () => {
        campo.value = campo.value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]/g, "");
    });
});

const alertaDiagnostico = document.querySelector("#diagnosticoAlerta");
if (alertaDiagnostico) {
    const guardada = sessionStorage.getItem("alertasServitech");
    const aplicarAlerta = datos => {
            const cantidad = datos.diagnosticos_pendientes || 0;
            alertaDiagnostico.textContent = cantidad;
            alertaDiagnostico.hidden = cantidad === 0;
    };
    if (guardada) aplicarAlerta(JSON.parse(guardada));
    fetch("/api/alertas")
        .then(respuesta => respuesta.json())
        .then(datos => {
            sessionStorage.setItem("alertasServitech", JSON.stringify(datos));
            aplicarAlerta(datos);
        }).catch(() => {});
}

window.addEventListener("load", () => {
    document.querySelectorAll(".sidebar a[href^='/']").forEach(enlace => {
        const prefetch = document.createElement("link");
        prefetch.rel = "prefetch";
        prefetch.href = enlace.getAttribute("href");
        document.head.appendChild(prefetch);
    });
});

document.querySelectorAll(".solo-numeros").forEach(campo => {
    campo.addEventListener("input", () => {
        campo.value = campo.value.replace(/\D/g, "");
    });
});

const tipoEquipo = document.querySelector("#tipoEquipo");
const tipoOtroGrupo = document.querySelector("#tipoOtroGrupo");
const tipoOtro = document.querySelector("#tipoOtro");
if (tipoEquipo) {
    tipoEquipo.addEventListener("change", () => {
        const mostrar = tipoEquipo.value === "Otro";
        tipoOtroGrupo.hidden = !mostrar;
        tipoOtro.required = mostrar;
        if (!mostrar) tipoOtro.value = "";
    });
}

const accesorioOpcion = document.querySelector("#accesorioOpcion");
const accesoriosDetalleGrupo = document.querySelector("#accesoriosDetalleGrupo");
const accesoriosDetalle = document.querySelector("#accesoriosDetalle");
if (accesorioOpcion) {
    accesorioOpcion.addEventListener("change", () => {
        const mostrar = accesorioOpcion.value === "Especificar";
        accesoriosDetalleGrupo.hidden = !mostrar;
        accesoriosDetalle.required = mostrar;
        if (!mostrar) accesoriosDetalle.value = "";
    });
}

function imprimirTicket() {
    const ticket = document.getElementById("ticketImprimible");
    if (!ticket) return;
    const padreOriginal = ticket.parentNode;
    const siguienteOriginal = ticket.nextSibling;
    let restaurado = false;
    const restaurarTicket = () => {
        if (restaurado) return;
        restaurado = true;
        document.body.classList.remove("printing-ticket");
        padreOriginal.insertBefore(ticket, siguienteOriginal);
        window.removeEventListener("afterprint", restaurarTicket);
    };

    document.body.classList.add("printing-ticket");
    document.body.appendChild(ticket);
    window.addEventListener("afterprint", restaurarTicket, { once: true });
    window.print();
    setTimeout(restaurarTicket, 1000);
}

document.querySelectorAll(".password-toggle").forEach(boton => {
    boton.addEventListener("click", () => {
        const campo = document.getElementById(boton.dataset.target);
        if (!campo) return;
        const mostrar = campo.type === "password";
        campo.type = mostrar ? "text" : "password";
        const icono = boton.querySelector("i");
        icono.className = mostrar ? "bi bi-eye-slash" : "bi bi-eye";
    });
});
