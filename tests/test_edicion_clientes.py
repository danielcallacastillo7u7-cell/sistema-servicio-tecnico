import unittest
from test_multi_equipos import MultiplesEquipos, SessionLocal, Cliente, OrdenServicio

class EdicionClientes(unittest.TestCase):
    def setUp(self):
        self.base=MultiplesEquipos();self.base.setUp();self.base.guardar([self.base.uno])
        self.web=self.base.web
        self.original=self.web.get('/clientes/api').json()['clientes'][0]
        self.original={k:self.original[k] for k in ['nombres','apellidos','dni_ruc','telefono']}
    def test_edicion_ticket_historial(self):
        datos={**self.original,'nombres':'Juana','telefono':'912345678','original':self.original}
        r=self.web.put('/clientes/api/1',json=datos);self.assertEqual(r.status_code,200,r.text)
        self.assertIn('Juana',self.web.get('/ordenes/1/ticket').text)
        self.assertIn('912345678',self.web.get('/ordenes/1/ticket').text)
        self.assertEqual(self.web.get('/clientes/api/1/historial').json()['cliente']['nombres'],'Juana')
        with SessionLocal() as db:self.assertEqual(db.query(OrdenServicio).count(),1)
        self.assertEqual(self.web.put('/clientes/api/1',json=datos).status_code,409)
    def test_duplicado_invalido_y_ausente(self):
        with SessionLocal() as db:
            db.add(Cliente(nombres='Otra',apellidos='Persona',dni_ruc='87654321',telefono='987654321'));db.commit()
        datos={**self.original,'original':self.original,'dni_ruc':'87654321'}
        self.assertEqual(self.web.put('/clientes/api/1',json=datos).status_code,409)
        datos={**self.original,'original':self.original,'telefono':'123'}
        self.assertEqual(self.web.put('/clientes/api/1',json=datos).status_code,422)
        self.assertEqual(self.web.put('/clientes/api/999',json={**self.original,'original':self.original}).status_code,404)
        self.assertEqual(self.web.get('/clientes/api/1/historial').json()['cliente']['dni_ruc'],self.original['dni_ruc'])
    def test_diagnostico_desde_historial(self):
        r=self.web.post('/diagnosticos',data=dict(orden_id=1,falla_encontrada='Falla',solucion_recomendada='Revisar',repuestos_necesarios='',costo_estimado='10'),follow_redirects=False)
        self.assertEqual(r.status_code,303,r.text)
        d=self.web.get('/clientes/api/1/historial').json()['ordenes'][0]['diagnostico']
        r=self.web.put('/diagnosticos/api/'+str(d['id']),json=dict(falla_encontrada='Corregida',solucion_recomendada='Cambio',repuestos_necesarios='Cable',costo_estimado='25'))
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.web.get('/clientes/api/1/historial').json()['ordenes'][0]['diagnostico']['falla'],'Corregida')
        self.assertIn('editarClienteForm',self.web.get('/clientes').text)
        self.assertIn('editarDiagnosticoModal',self.web.get('/clientes').text)

if __name__=='__main__':unittest.main()
