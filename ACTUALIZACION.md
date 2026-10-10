# ServiTech: varios equipos en una orden

Preparado sobre la copia local del 4 de septiembre de 2026. Esta entrega es una copia actualizada; no se reemplazó la instalación ni se modificó la base real.

## Aplicación

1. Conserva una copia de tu proyecto y un respaldo de PostgreSQL antes de actualizar.
2. Detén ServiTech y coloca los archivos de esta entrega en la carpeta de tu instalación. Conserva tu archivo `.env`, tu entorno Python y cualquier archivo propio que no figure en esta entrega. El ZIP no contiene credenciales.
3. Inicia la aplicación con el procedimiento habitual (`uvicorn app.main:app`, desde la carpeta del proyecto).
4. Al iniciar, se crea `orden_equipos` y se asocia el equipo de cada orden anterior. La operación es aditiva e idempotente: se puede reiniciar sin duplicar asociaciones. La cuenta de PostgreSQL necesita permiso para crear la tabla y sus índices e insertar las asociaciones.
5. Abre Órdenes, registra dos equipos y revisa el ticket antes de imprimir.

No apliques esta copia sobre una versión posterior sin comparar los archivos: la base utilizada es del 4 de septiembre.

## Comportamiento

- Se mantiene la cuadrícula, los campos y el estilo de «Datos del equipo».
- Empieza con Equipo 1. «+ Agregar otro equipo» agrega un bloque vacío.
- Se pueden quitar equipos adicionales. La numeración se actualiza sin borrar los datos de los demás.
- «Otro» y «Especificar accesorios» funcionan por separado en cada equipo.
- El servidor valida todos los equipos. Una serie repetida, un equipo de otro cliente o un error de integridad revierte todo el registro.
- El formulario recupera los datos enviados cuando el servidor muestra un error.
- Una sola orden y un solo número de ticket incluyen todos los equipos, accesorios y observaciones. El comprobante y el buscador también los incluyen.
- Las exportaciones agregan `cantidad_equipos` y `equipos_recibidos` (JSON) y mantienen una fila por orden para no duplicar importes ni la clave de sincronización. Los campos singulares anteriores siguen identificando el primer equipo.

## Persistencia y compatibilidad

`orden_equipos` vincula cada orden con sus equipos, guarda su posición y una copia de tipo, marca, modelo, serie, accesorios y observaciones al recibirlos. Un equipo puede volver en otra orden sin perder su historial ni alterar los nuevos tickets anteriores.

Se conserva `ordenes_servicio.equipo_id` como referencia al primer equipo para compatibilidad. No se eliminan columnas ni órdenes anteriores. Los envíos antiguos con campos de un solo equipo siguen funcionando. Las órdenes sin asociaciones tienen una lectura de respaldo de su equipo original.

La migración copia los datos disponibles al momento de ejecutarse; no puede reconstruir datos históricos que ya se hubieran sobrescrito antes de esta actualización.

El técnico, la falla reportada, el diagnóstico y el estado siguen siendo **por orden**, como en el flujo existente. Las observaciones individuales permiten detallar cada equipo. El seguimiento y las entregas parciales por equipo requieren una ampliación posterior.

## Verificación

Pruebas de integración en SQLite temporal con claves foráneas activadas: guardado múltiple, tickets, búsqueda del segundo equipo, exportación, formulario antiguo, validaciones, reversión, reutilización de un equipo, migración repetida, eliminación y estados. No se ejecutaron contra PostgreSQL real ni se probó una impresora física.

Pruebas del formulario con JSDOM: agregar, quitar, renumerar, conservar datos, identificadores únicos, campos condicionales, serializar y restaurar.

Para ejecutar las pruebas en un entorno de desarrollo con las dependencias del proyecto:

```text
pip install httpx
python tests/test_multi_equipos.py
npm install --no-save jsdom
node tests/test_formulario.cjs
```

Las pruebas Python fuerzan una base temporal propia y no usan la conexión real del `.env`.
