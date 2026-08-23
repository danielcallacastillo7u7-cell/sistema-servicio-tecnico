const buscador = document.querySelector("#buscadorGlobal");
const resultados = document.querySelector("#resultadosBusqueda");
let temporizador;

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
            resultados.innerHTML = datos.length
                ? datos.map(item => {
                    const especificaciones = item.especificaciones
                        ? `<div class="search-specs"><strong>Especificaciones</strong><span><b>Falla:</b> ${item.especificaciones.falla_encontrada}</span><span><b>Solución:</b> ${item.especificaciones.solucion}</span><span><b>Repuestos:</b> ${item.especificaciones.repuestos}</span><span><b>Costo:</b> S/ ${item.especificaciones.costo}</span></div>`
                        : '<div class="search-specs pending"><strong>Especificaciones</strong><span>Pendiente de diagnóstico.</span></div>';
                    return `<a class="search-item detailed" href="/ordenes?ticket=${item.id}"><div><strong>${item.numero}</strong><small>${item.estado}</small></div><div><span>${item.cliente}</span><span>${item.equipo}</span></div>${especificaciones}</a>`;
                }).join("")
                : '<p class="text-secondary mb-0">No se encontraron órdenes.</p>';
        }, 250);
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
    document.body.classList.add("printing-ticket");
    window.print();
    setTimeout(() => document.body.classList.remove("printing-ticket"), 300);
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
