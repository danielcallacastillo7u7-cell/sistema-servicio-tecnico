const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const raiz = path.resolve(__dirname, '..');
const plantilla = fs.readFileSync(path.join(raiz, 'app/templates/ordenes.html'), 'utf8')
    .replaceAll('{{ trabajador.nombre }}', 'Ana Técnica')
    .replace('{% if not trabajadores %}disabled{% endif %}', '');
const script = fs.readFileSync(path.join(raiz, 'app/static/js/orden-equipos.js'), 'utf8');
const tick = () => new Promise(resolve => setTimeout(resolve, 10));
function abrir(lan = false, previo = '{}') {
    const dom = new JSDOM(plantilla.replace('{{ (formulario_previo or {})|tojson }}', previo), { runScripts: 'outside-only', url:lan ? 'http://192.168.100.49:8000/ordenes' : 'http://localhost/ordenes' });
    if (lan) Object.defineProperty(dom.window.crypto, 'randomUUID', { value: undefined });
    for (const nombre of ['localStorage', 'sessionStorage']) {
        Object.defineProperty(dom.window, nombre, { get() { throw new Error('No leer estado residual'); } });
    }
    dom.window.eval(script);
    dom.window.document.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
    return dom;
}
async function main(lan = false) {
    const dom = abrir(lan);
    const w = dom.window, d = w.document;
    assert.equal(d.querySelectorAll('.equipo-bloque').length, 1, 'Equipo 1 visible sin cliente');
    dom.window.eval(script);
    d.dispatchEvent(new w.Event('DOMContentLoaded'));
    assert.equal(d.querySelectorAll('.equipo-bloque').length, 1, 'Inicialización única');
    const bloques = () => [...d.querySelectorAll('.equipo-bloque')];
    const campo = (i, name) => bloques()[i].querySelector(`[name="${name}"]`);
    const boton = i => bloques()[i].querySelector('.guardar-equipo');
    const llenar = i => {
        for (const [k,v] of Object.entries({ tipo:'Laptop', marca:'Lenovo', modelo:`Modelo ${i}`, accesorio_opcion:'Ninguno', falla_reportada:`Falla ${i}` })) campo(i,k).value=v;
    };
    for (const [k,v] of Object.entries({ nombres:'Juan', apellidos:'Perez', dni_ruc:'12345678', telefono:'987654321' })) d.querySelector(`#datosCliente [name="${k}"]`).value=v;
    assert.equal(d.querySelectorAll('[name="tecnico_responsable"]').length,1);
    assert.equal(d.getElementById('nuevoCliente'),null);
    d.getElementById('tecnicoResponsable').value='Ana Técnica';
    llenar(0);
    d.getElementById('agregarEquipo').click();
    d.getElementById('agregarEquipo').click();
    assert.equal(bloques().length,3);
    campo(2,'modelo').value='Conservar tercero';
    bloques()[1].querySelector('.quitar-equipo').click();
    assert.equal(campo(1,'modelo').value,'Conservar tercero');
    assert.equal(bloques()[1].querySelector('.equipo-numero').textContent,'Equipo 2');
    campo(1,'modelo').value='';
    const ids = [...d.querySelectorAll('.equipo-bloque [id]')].map(e=>e.id);
    assert.equal(new Set(ids).size,ids.length);
    const envios=[];
    let resolver;
    w.fetch = (_,options) => { envios.push(options.body); return new Promise(r=>{resolver=r;}); };
    boton(0).click();
    boton(0).click();
    assert.equal(envios.length,1,'Un doble clic no envía dos veces');
    assert.equal(new URLSearchParams(envios[0]).get('modelo'),'Modelo 0');
    resolver({ok:true,json:async()=>({id:1,numero_orden:'OT-1',estado:'Recibido',ticket_url:'/ordenes/1/ticket'})});
    await tick();
    assert.equal(bloques()[0].dataset.guardado,'true');
    assert.equal(boton(0).disabled,true);
    assert.equal(boton(1).disabled,false);
    assert.equal(campo(1,'modelo').value,'');
    assert.equal(d.querySelector('[name="dni_ruc"]').value,'12345678');
    assert.equal(d.querySelector('[name="dni_ruc"]').readOnly,true);
    assert.equal(bloques()[0].querySelector('.equipo-ticket').open,true);
    assert.equal(bloques()[0].querySelector('iframe').getAttribute('src'),'/ordenes/1/ticket');
    assert.equal(w.location.href,lan ? 'http://192.168.100.49:8000/ordenes' : 'http://localhost/ordenes');
    assert.match(new URLSearchParams(envios[0]).get('solicitud_token'), /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
    boton(1).click();
    assert.equal(envios.length,1,'El segundo equipo vacío debe validarse por separado');
    llenar(1);
    w.fetch = async (_, options) => { envios.push(options.body); return {ok:false,status:400,json:async()=>({detail:'Revisa el modelo'})}; };
    boton(1).click();
    await tick();
    assert.equal(bloques()[1].querySelector('.equipo-error').textContent,'Revisa el modelo');
    assert.equal(campo(1,'modelo').disabled,false);
    assert.equal(boton(0).disabled,true);
    w.fetch = async (_,options)=>{envios.push(options.body);throw new Error('Conexión interrumpida');};
    boton(1).click();
    await tick();
    const incierto=envios.at(-1);
    assert.equal(boton(1).textContent,'Comprobar guardado');
    assert.equal(campo(1,'modelo').disabled,true);
    assert.equal(d.getElementById('tecnicoResponsable').disabled,true);
    w.fetch = async (_,options)=>{envios.push(options.body);return {ok:true,json:async()=>({id:2,numero_orden:'OT-2',estado:'Recibido',ticket_url:'/ordenes/2/ticket'})};};
    boton(1).click();
    await tick();
    assert.equal(envios.at(-1),incierto,'Reintento conserva token y datos');
    assert.notEqual(new URLSearchParams(envios[0]).get('solicitud_token'),new URLSearchParams(incierto).get('solicitud_token'));
    assert.equal(bloques()[1].dataset.guardado,'true');
    assert.equal(d.querySelectorAll('#ordenesRegistradas tbody tr').length >= 2,true);
    assert.equal(d.querySelector('[name="nombres"]').value,'Juan');
    assert.equal(new URLSearchParams(envios[0]).get('tecnico_responsable'),'Ana Técnica');
    assert.equal(new URLSearchParams(envios.at(-1)).get('tecnico_responsable'),'Ana Técnica');
    assert.equal(d.getElementById('tecnicoResponsable').value,'Ana Técnica');
    dom.window.close();
    console.log('OK: guardado independiente, mismo cliente, doble clic, validación por bloque, errores, reintento, ticket embebido y técnico compartido.');
}
async function todas() {
    await main(false);
    await main(true);
    for (const previo of ['null', '[]', '{invalido', '{"equipos_json":"[]"}']) {
        const dom = abrir(true, previo);
        assert.equal(dom.window.document.querySelectorAll('.equipo-bloque').length, 1);
        dom.window.close();
    }
    console.log('OK: localhost y LAN sin randomUUID, almacenamiento bloqueado, estado inicial inválido e inicialización repetida.');
}
todas().catch(e=>{console.error(e);process.exitCode=1;});
