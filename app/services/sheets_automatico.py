"""Espejo de órdenes por mes; nunca modifica pestañas ajenas."""
import os
import json
import hashlib
import threading
import time
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.database import SessionLocal
from app.services import sheets_conexiones as conexiones
from app.services.exportaciones import obtener_filas, extraer_spreadsheet_id

MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
COLUMNAS = ['ID orden','Orden','Fecha de ingreso (Perú)','Estado','Técnico','Cliente','DNI/RUC','Celular','Falla reportada','Equipos recibidos','Falla encontrada','Solución recomendada','Costo estimado']
PREFIX = 'Órdenes - '
_stop = threading.Event()
_wake = threading.Event()
_thread = None
_status_lock = threading.Lock()
_status = dict(estado='Pendiente',mensaje='Esperando conexión',ultima=None,ordenes=0)

def estado():
    with _status_lock: result = dict(_status)
    config=conexiones.actual()
    result['enlace'] = 'https://docs.google.com/spreadsheets/d/'+config['hoja']+'/edit' if config else ''
    result['activo'] = bool(config)
    return result

def informar(**valores):
    with _status_lock: _status.update(valores)

def agrupar(filas):
    grupos={}
    for f in filas:
        fecha=datetime.fromisoformat(f['fecha_ingreso'])
        if fecha.tzinfo is None: fecha=fecha.replace(tzinfo=timezone.utc)
        fecha=fecha.astimezone(timezone(timedelta(hours=-5)))
        nombre=f'{PREFIX}{MESES[fecha.month-1]} {fecha.year}'
        equipos=json.loads(f['equipos_recibidos'])
        texto='\n'.join(' | '.join(str(e.get(k) or '') for k in ['tipo','marca','modelo','numero_serie','accesorios','observaciones']) for e in equipos)
        grupos.setdefault(nombre,[]).append([str(f['id_orden']),f['numero_orden'],fecha.strftime('%d/%m/%Y %H:%M'),f['estado'],f['tecnico_responsable'],f['cliente'],f['dni_ruc'],f['telefono'],f['falla_reportada'],texto,f['falla_encontrada'],f['solucion_recomendada'],str(f['costo_estimado'])])
    return grupos

def servicio(config):
    return conexiones.api_actual(config)

def enviar(grupos,config):
    sid=config['hoja']
    api=servicio(config)
    meta=api.get(spreadsheetId=sid,fields='sheets.properties').execute()
    existentes={s['properties']['title']:s['properties'] for s in meta.get('sheets',[])}
    nombres=set(grupos)|{n for n in existentes if n.startswith(PREFIX)}
    requests=[]
    used={p['sheetId'] for p in existentes.values()}
    # Solo se sobrescriben pestañas con nuestra cabecera; las otras se preservan.
    targets=sorted(nombres & existentes.keys())
    if targets:
        headers=api.values().batchGet(spreadsheetId=sid,ranges=["'"+n.replace("'","''")+"'!A1:M1" for n in targets]).execute().get('valueRanges',[])
        for name,header in zip(targets,headers):
            if header.get('values',[]) != [COLUMNAS]:
                raise ValueError('La pestaña '+name+' contiene datos ajenos. Renómbrala antes de sincronizar.')
    for name in sorted(nombres):
        values=[COLUMNAS]+grupos.get(name,[])
        if name not in existentes:
            sh=max(used,default=0)+1;used.add(sh)
            requests.append({'addSheet':{'properties':{'sheetId':sh,'title':name,'gridProperties':{'rowCount':max(100,len(values)),'columnCount':13,'frozenRowCount':1}}}})
            count=max(100,len(values));cols=13
        else:
            props=existentes[name];sh=props['sheetId'];count=max(props['gridProperties']['rowCount'],len(values));cols=max(13,props['gridProperties']['columnCount'])
            requests.append({'updateSheetProperties':{'properties':{'sheetId':sh,'gridProperties':{'rowCount':count,'columnCount':cols,'frozenRowCount':1}},'fields':'gridProperties'}})
        rows=[{'values':[{'userEnteredValue':{'stringValue':str(v or '')}} for v in row]} for row in values]
        requests.append({'updateCells':{'range':{'sheetId':sh,'startRowIndex':0,'endRowIndex':count,'startColumnIndex':0,'endColumnIndex':13},'rows':rows,'fields':'userEnteredValue'}})
        requests.extend([
            {'repeatCell':{'range':{'sheetId':sh,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':0,'endColumnIndex':13},'cell':{'userEnteredFormat':{'backgroundColor':{'red':.09,'green':.13,'blue':.18},'textFormat':{'bold':True,'foregroundColor':{'red':1,'green':1,'blue':1}}}},'fields':'userEnteredFormat'}},
            {'updateDimensionProperties':{'range':{'sheetId':sh,'dimension':'COLUMNS','startIndex':0,'endIndex':13},'properties':{'pixelSize':180},'fields':'pixelSize'}},
            {'setBasicFilter':{'filter':{'range':{'sheetId':sh,'startRowIndex':0,'endRowIndex':len(values),'startColumnIndex':0,'endColumnIndex':13}}}}
        ])
    if requests: api.batchUpdate(spreadsheetId=sid,body={'requests':requests}).execute()

def solicitar():
    _wake.set()

def ciclo():
    last_hash=None;last_check=0;failures=0
    while not _stop.is_set():
        forced=_wake.is_set();_wake.clear()
        config=conexiones.actual()
        if not config:
            informar(estado='Desactivado',mensaje='Selecciona una conexión para activar la sincronización.',ultima=None,ordenes=0)
        else:
            try:
                with SessionLocal() as db: grupos=agrupar(obtener_filas(db,'completo'))
                fingerprint=hashlib.sha256(json.dumps([config['id'],grupos],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                if forced or fingerprint!=last_hash or time.monotonic()-last_check>300:
                    informar(estado='Sincronizando',mensaje='Actualizando órdenes por mes…')
                    with conexiones.LOCK:
                        if conexiones.actual()!=config: continue
                        enviar(grupos,config)
                        last_hash=fingerprint;last_check=time.monotonic()
                        informar(estado='Conectado',mensaje='Órdenes actualizadas por mes. Las ediciones se realizan en ServiTech.',ultima=datetime.now(timezone(timedelta(hours=-5))).strftime('%d/%m/%Y %H:%M:%S'),ordenes=sum(map(len,grupos.values())))
                failures=0
            except HttpError as exc:
                failures+=1
                code=exc.resp.status
                informar(estado='Error',mensaje='Comparte la hoja con la cuenta de servicio como Editor.' if code in (403,404) else 'Google no respondió correctamente. Se reintentará automáticamente.')
            except ValueError as exc:
                failures+=1;informar(estado='Error',mensaje=str(exc)[:220])
            except Exception:
                failures+=1;informar(estado='Error',mensaje='No se pudo conectar. Revisa internet y la configuración; se reintentará automáticamente.')
        _wake.wait(min(300,5*2**min(failures,6)))

def iniciar():
    global _thread
    if _thread and _thread.is_alive(): return
    conexiones.importar_anterior()
    _stop.clear();_thread=threading.Thread(target=ciclo,name='servitech-sheets',daemon=True);_thread.start()

def detener():
    _stop.set();_wake.set()
    if _thread: _thread.join(timeout=2)
