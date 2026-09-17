"""Pruebas aisladas: nunca se utiliza DATABASE_URL del proyecto."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
temporal = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(temporal.name) / 'prueba.db')
os.environ['CLAVE_ELIMINACION'] = 'clave-pruebas'

from fastapi.testclient import TestClient
from sqlalchemy import event
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.cliente import Cliente
from app.models.equipo import Equipo
from app.models.orden import OrdenServicio
from app.models.orden_equipo import OrdenEquipo
from app.models.trabajador import Trabajador
from app.models.historial import HistorialEstado
from app.migraciones import migrar_equipos_orden
from app.services.exportaciones import obtener_filas

# Activar claves foráneas en todas las conexiones de prueba.
engine.dispose()
@event.listens_for(engine, 'connect')
def activar_fk(conexion, _):
    conexion.execute('PRAGMA foreign_keys=ON')


class MultiplesEquipos(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.web = TestClient(app)
        with SessionLocal() as db:
            db.add(Trabajador(nombre='Ana Técnica'))
            db.commit()
        self.cliente = dict(nombres='Juan', apellidos='Perez', dni_ruc='12345678', telefono='987654321', falla_reportada='Revisar equipos', tecnico_responsable='Ana Técnica')
        self.uno = dict(tipo='Laptop', marca='Lenovo', modelo='IdeaPad', numero_serie='SERIE-LAPTOP', accesorio_opcion='Especificar', accesorios_detalle='Cargador', observaciones='No enciende')
        self.dos = dict(tipo='Impresora', marca='Epson', modelo='L3250', numero_serie='SERIE-IMPRESORA', accesorio_opcion='Ninguno', observaciones='No imprime')

    def guardar(self, equipos=None, **cambios):
        datos = dict(self.cliente)
        datos.update(cambios)
        if equipos is not None:
            datos['equipos_json'] = json.dumps(equipos)
        return self.web.post('/ordenes', data=datos, follow_redirects=False)

    def test_varios_ticket_busqueda_exportacion(self):
        r = self.guardar([self.uno, self.dos])
        self.assertEqual(r.status_code, 303, r.text)
        with SessionLocal() as db:
            self.assertEqual(db.query(OrdenServicio).count(), 1)
            self.assertEqual(db.query(OrdenEquipo).count(), 2)
            self.assertEqual(db.query(Cliente).count(), 1)
            self.assertEqual(db.query(HistorialEstado).count(), 1)
            filas = obtener_filas(db, 'completo')
            self.assertEqual(len(filas), 1)
            self.assertEqual(len(json.loads(filas[0]['equipos_recibidos'])), 2)
        for url in [r.headers['location'], '/ordenes/1/comprobante']:
            pagina = self.web.get(url)
            self.assertEqual(pagina.status_code, 200)
            for texto in ['SERIE-LAPTOP', 'SERIE-IMPRESORA', 'No imprime', 'No enciende']:
                self.assertIn(texto, pagina.text)
        hallados = self.web.get('/api/buscar?q=SERIE-IMPRESORA').json()
        self.assertEqual(len(hallados), 1)
        self.assertEqual(len(hallados[0]['equipos']), 2)
        for url in ['/', '/?estado=Todas', '/diagnosticos', '/exportaciones']:
            self.assertEqual(self.web.get(url).status_code, 200)

    def test_formulario_anterior(self):
        self.assertEqual(self.guardar(None, **self.uno).status_code, 303)

    def test_historial_clientes_y_equipo_recurrente(self):
        self.guardar_individual(self.uno)
        self.guardar_individual(self.dos)
        self.guardar_individual(dict(self.uno,observaciones='Segunda visita'))
        self.guardar_individual(dict(self.dos,numero_serie='AJENA'),dni_ruc='87654321',nombres='Pedro')
        respuesta = self.web.get('/clientes/api?q=Juan%20Perez').json()
        self.assertEqual(respuesta['total'],1)
        historial = self.web.get('/clientes/api/1/historial').json()
        self.assertEqual(historial['total'],3)
        self.assertEqual(len(historial['equipos']),2)
        self.assertEqual({o['id'] for o in historial['ordenes']},{1,2,3})
        filtrado = self.web.get('/clientes/api/1/historial?equipo_id=1').json()
        self.assertEqual({o['id'] for o in filtrado['ordenes']},{1,3})
        self.assertEqual(self.web.get('/clientes/api/1/historial?q=SERIE-IMPRESORA').json()['total'],1)
        self.assertEqual(self.web.get('/clientes/api/1/historial?equipo_id=3').status_code,404)
        self.assertEqual(self.web.get('/clientes/api/999/historial').status_code,404)
        antiguos = {o['id']:o for o in historial['ordenes']}
        self.assertEqual(antiguos[1]['equipos'][0]['observaciones'],'No enciende')
        self.assertEqual(antiguos[3]['equipos'][0]['observaciones'],'Segunda visita')
        self.web.post('/diagnosticos',data={'orden_id':1,'falla_encontrada':'Placa','solucion_recomendada':'Reparar placa','costo_estimado':'100'},follow_redirects=False)
        h = self.web.get('/clientes/api/1/historial?q=Reparar%20placa').json()
        self.assertEqual(h['total'],1)
        self.assertEqual(h['ordenes'][0]['diagnostico']['costo'],'100.00')
        self.assertEqual(h['ordenes'][0]['historial'][0]['estado'],'Recibido')

    def test_historial_paginado_y_clientes_sin_ordenes(self):
        with SessionLocal() as db:
            db.add_all([Cliente(nombres=f'Cliente {i}',apellidos='Prueba',dni_ruc=str(10000000+i),telefono='987654321') for i in range(23)])
            db.commit()
        a = self.web.get('/clientes/api').json()
        b = self.web.get('/clientes/api?pagina=2').json()
        self.assertEqual((a['total'],len(a['clientes']),len(b['clientes'])),(23,20,3))
        self.assertFalse({c['id'] for c in a['clientes']} & {c['id'] for c in b['clientes']})
        self.assertEqual(self.web.get('/clientes/api/1/historial').json()['total'],0)
        self.assertEqual(self.web.get('/clientes/api?q=%25').json()['total'],0)

    def test_historial_multiequipo_y_paginacion(self):
        self.guardar([self.uno,self.dos])
        for _ in range(10):
            self.guardar_individual(self.uno)
        primera=self.web.get('/clientes/api/1/historial').json()
        segunda=self.web.get('/clientes/api/1/historial?pagina=2').json()
        self.assertEqual((primera['total'],len(primera['ordenes']),len(segunda['ordenes'])),(11,10,1))
        filtrado=self.web.get('/clientes/api/1/historial?equipo_id=2').json()
        self.assertEqual(filtrado['total'],1)
        self.assertEqual(len(filtrado['ordenes'][0]['equipos']),2)

    def test_diagnostico_desde_inicio_selecciona_orden_exacta(self):
        self.guardar_individual(self.uno)
        self.guardar_individual(self.dos)
        inicio = self.web.get('/?estado=Recibido').text
        self.assertIn('/diagnosticos?orden_id=1',inicio)
        self.assertIn('/diagnosticos?orden_id=2',inicio)
        pagina = self.web.get('/diagnosticos?orden_id=1')
        self.assertEqual(pagina.status_code,200)
        self.assertRegex(pagina.text,r'value="1"\s+selected')
        self.assertNotRegex(pagina.text,r'value="2"\s+selected')
        self.assertNotRegex(self.web.get('/diagnosticos').text,r'value="[12]"\s+selected')
        error = self.web.post('/diagnosticos',data={'orden_id':1,'falla_encontrada':'Falla','solucion_recomendada':'Reparar','costo_estimado':'-1'})
        self.assertEqual(error.status_code,400)
        self.assertRegex(error.text,r'value="1"\s+selected')
        guardado = self.web.post('/diagnosticos',data={'orden_id':1,'falla_encontrada':'Falla','solucion_recomendada':'Reparar','costo_estimado':'10'},follow_redirects=False)
        self.assertEqual(guardado.status_code,303)
        with SessionLocal() as db:
            self.assertIsNotNone(db.get(OrdenServicio,1).diagnostico)
            self.assertIsNone(db.get(OrdenServicio,2).diagnostico)
        self.assertEqual(self.web.get('/diagnosticos?orden_id=1').status_code,409)
        self.assertEqual(self.web.get('/diagnosticos?orden_id=999999').status_code,404)

    def test_dni_existente_no_se_modifica_desde_ordenes(self):
        self.guardar([self.uno])
        for cambios in [dict(nombres='Pedro'), dict(apellidos='Gomez'), dict(telefono='999999999')]:
            r = self.guardar_individual(self.dos, **cambios)
            self.assertEqual(r.status_code, 409)
        r = self.guardar([self.dos], nombres='Pedro')
        self.assertEqual(r.status_code, 409)
        with SessionLocal() as db:
            cliente = db.query(Cliente).one()
            self.assertEqual((cliente.nombres,cliente.apellidos,cliente.telefono),('Juan','Perez','987654321'))
            self.assertEqual(db.query(OrdenServicio).count(),1)
            self.assertEqual(db.query(Equipo).count(),1)
        self.assertEqual(self.guardar_individual(self.dos).status_code,200)

    def test_busqueda_exacta_dni(self):
        self.guardar([self.uno])
        r = self.web.get('/clientes/por-documento/12345678')
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['nombres'],'Juan')
        self.assertEqual(self.web.get('/clientes/por-documento/87654321').json(),{'encontrado':False})
        self.assertEqual(self.web.get('/clientes/por-documento/123').status_code,400)

    def test_equipos_no_sobrescribe_cliente(self):
        self.guardar([self.uno])
        r = self.web.post('/equipos',data={**self.cliente,**self.dos,'nombres':'Pedro'},follow_redirects=False)
        self.assertEqual(r.status_code,409)
        with SessionLocal() as db:
            self.assertEqual(db.query(Cliente).one().nombres,'Juan')
            self.assertEqual(db.query(Equipo).count(),1)

    def guardar_individual(self, equipo, token=None, **cambios):
        datos = {**self.cliente, **equipo, 'solicitud_token': token or str(uuid4()), **cambios}
        return self.web.post('/ordenes/guardar-equipo', data=datos, follow_redirects=False)

    def test_tickets_independientes_mismo_cliente(self):
        primero = self.guardar_individual(self.uno)
        segundo = self.guardar_individual(self.dos, falla_reportada='Falla impresora')
        self.assertEqual(primero.status_code, 200, primero.text)
        self.assertEqual(segundo.status_code, 200, segundo.text)
        self.assertNotEqual(primero.json()['numero_orden'], segundo.json()['numero_orden'])
        self.assertNotIn('location', primero.headers)
        with SessionLocal() as db:
            self.assertEqual(db.query(Cliente).count(), 1)
            self.assertEqual(db.query(OrdenServicio).count(), 2)
            for orden in db.query(OrdenServicio).all():
                self.assertEqual(len(orden.equipos_recibidos), 1)
        ticket = self.web.get(primero.json()['ticket_url'])
        self.assertEqual(ticket.status_code, 200)
        self.assertIn('SERIE-LAPTOP', ticket.text)
        self.assertNotIn('SERIE-IMPRESORA', ticket.text)
        self.assertIn('ticketImprimible', ticket.text)
        self.assertIn('SERIE-IMPRESORA', self.web.get(segundo.json()['ticket_url']).text)

    def test_reintento_recupera_ticket_sin_duplicar(self):
        token = str(uuid4())
        primero = self.guardar_individual(self.uno, token)
        segundo = self.guardar_individual(self.uno, token)
        self.assertEqual(primero.json(), segundo.json())
        conflicto = self.guardar_individual(self.dos, token)
        self.assertEqual(conflicto.status_code, 409)
        with SessionLocal() as db:
            self.assertEqual(db.query(OrdenServicio).count(), 1)

    def test_error_individual_conserva_primera_orden(self):
        self.guardar_individual(self.uno)
        malo = self.guardar_individual(dict(self.dos, modelo=''))
        self.assertEqual(malo.status_code, 400)
        self.assertIn('detail', malo.json())
        with SessionLocal() as db:
            self.assertEqual(db.query(OrdenServicio).count(), 1)
        self.assertEqual(self.guardar_individual(self.dos).status_code, 200)

    def test_individual_rechaza_lote_y_token_invalido(self):
        r = self.guardar_individual(self.uno, equipos_json=json.dumps([self.uno, self.dos]))
        self.assertEqual(r.status_code, 400)
        r = self.guardar_individual(self.uno, token='invalido')
        self.assertEqual(r.status_code, 400)

    def test_invalidos_sin_guardado_parcial(self):
        for equipos in [[], [self.uno, dict(self.dos, modelo=' ')], [self.uno, self.uno], [dict(self.uno, tipo='Otro')], [dict(self.uno, accesorios_detalle='')], [dict(self.uno, modelo='x'*101)], {'tipo':'Laptop'}, [42]]:
            with self.subTest(equipos=equipos):
                self.assertEqual(self.guardar(equipos).status_code, 400)
                with SessionLocal() as db:
                    self.assertEqual(db.query(Cliente).count(), 0)
                    self.assertEqual(db.query(Equipo).count(), 0)
                    self.assertEqual(db.query(OrdenServicio).count(), 0)

    def test_json_invalido(self):
        self.assertEqual(self.guardar(None, equipos_json='{').status_code, 400)

    def test_serie_otro_cliente_revierte_todo(self):
        self.guardar([self.dos])
        r = self.guardar([self.uno, self.dos], dni_ruc='87654321')
        self.assertEqual(r.status_code, 409)
        self.assertIn('formularioPrevio', r.text)
        self.assertIn('SERIE-LAPTOP', r.text)
        with SessionLocal() as db:
            self.assertEqual(db.query(Cliente).count(), 1)
            self.assertEqual(db.query(Equipo).count(), 1)
            self.assertEqual(db.query(OrdenServicio).count(), 1)

    def test_historial_equipo_reutilizado(self):
        self.guardar([self.uno, self.dos])
        self.guardar([dict(self.uno, accesorios_detalle='Sin cargador', observaciones='Pantalla rota')])
        with SessionLocal() as db:
            self.assertEqual(db.query(Equipo).count(), 2)
            self.assertEqual(db.query(OrdenEquipo).count(), 3)
        ticket = self.web.get('/ordenes?ticket=1').text
        self.assertIn('Cargador', ticket)
        self.assertIn('No enciende', ticket)
        self.assertNotIn('Pantalla rota', ticket)

    def test_migracion_orden_antigua_idempotente(self):
        self.guardar([self.uno])
        with SessionLocal() as db:
            db.query(OrdenEquipo).delete()
            db.commit()
        self.assertIn('SERIE-LAPTOP', self.web.get('/ordenes?ticket=1').text)
        migrar_equipos_orden(engine)
        migrar_equipos_orden(engine)
        with SessionLocal() as db:
            self.assertEqual(db.query(OrdenEquipo).count(), 1)

    def test_eliminar_orden_conserva_equipos(self):
        self.guardar([self.uno, self.dos])
        r = self.web.post('/ordenes/1/eliminar', data={'clave':'clave-pruebas'}, follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        with SessionLocal() as db:
            self.assertEqual(db.query(OrdenEquipo).count(), 0)
            self.assertEqual(db.query(Equipo).count(), 2)

    def test_estado_y_cancelacion(self):
        self.guardar([self.uno, self.dos])
        r = self.web.post('/ordenes/1/estado-rapido', data={'nuevo_estado':'Diagnosticado'}, follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        r = self.web.post('/ordenes/1/cancelar', data={'motivo':'El cliente ya no desea el servicio'}, follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        with SessionLocal() as db:
            self.assertEqual(db.get(OrdenServicio,1).estado, 'Cancelado')
            self.assertEqual(db.query(OrdenEquipo).count(), 2)


def tearDownModule():
    engine.dispose()
    temporal.cleanup()


if __name__ == '__main__':
    unittest.main(verbosity=2)
