# Tickets independientes en la misma pantalla

Esta actualización sustituye el flujo de guardar todos los equipos con un solo botón.

- Los datos del cliente se escriben una sola vez y permanecen visibles.
- Cada bloque tiene su falla reportada, técnico y botón «Guardar y generar ticket».
- Cada guardado crea una orden independiente con un equipo; no recarga la página.
- El equipo guardado queda marcado «Ticket listo», con su número, vista e impresión dentro del bloque.
- «Ticket listo» confirma el registro; el estado técnico inicial de la orden sigue siendo «Recibido».
- Los otros equipos conservan sus campos y botones pendientes.
- Después del primer registro, los datos del cliente quedan protegidos contra cambios accidentales. «Atender otro cliente» permite empezar una nueva atención sin borrar las órdenes guardadas.
- Ante una respuesta incierta, «Comprobar guardado» reenvía la misma solicitud y recupera el ticket sin duplicar la orden.

Se crea automáticamente la tabla aditiva `solicitudes_equipo` al iniciar. Las órdenes anteriores, incluidas las que contienen varios equipos, se conservan. No se dividen ni se eliminan registros existentes.

Verificación: 13 pruebas de integración aisladas, pruebas del formulario y flujo completo en navegador de escritorio y móvil. Las pruebas de creación usan una base temporal, no la base real del taller.
