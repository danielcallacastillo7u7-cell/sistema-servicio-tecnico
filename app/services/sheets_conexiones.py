import json
import os
import threading
from pathlib import Path
from uuid import uuid4
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from app.services.exportaciones import extraer_spreadsheet_id

LOCK = threading.RLock()

def carpeta():
    return Path(os.getenv('SERVITECH_CONNECTIONS_DIR', str(Path.home()/'AppData/Local/ServiTech/conexiones')))

def guardar_store(data):
    folder=carpeta();folder.mkdir(parents=True,exist_ok=True)
    temp=folder/'conexiones.tmp';temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');temp.replace(folder/'conexiones.json')

def leer():
    p=carpeta()/'conexiones.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'activa':None,'cuentas':[]}

def validar_json(raw):
    if len(raw)>64000:raise ValueError('El archivo JSON es demasiado grande (máximo 64 KB).')
    try: info=json.loads(raw)
    except Exception:raise ValueError('El archivo no es un JSON válido.') from None
    if not isinstance(info,dict) or info.get('type')!='service_account' or not str(info.get('client_email','')).endswith('.iam.gserviceaccount.com'):
        raise ValueError('Selecciona el JSON de una cuenta de servicio de Google.')
    if info.get('token_uri')!='https://oauth2.googleapis.com/token':raise ValueError('El archivo no contiene el servidor de acceso oficial de Google.')
    try: Credentials.from_service_account_info(info,scopes=['https://www.googleapis.com/auth/spreadsheets'])
    except Exception:raise ValueError('La clave del archivo JSON no es válida.') from None
    return info

def cliente(info):
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    creds=Credentials.from_service_account_info(info,scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return build('sheets','v4',http=AuthorizedHttp(creds,http=httplib2.Http(timeout=20)),cache_discovery=False).spreadsheets()

def nueva(nombre,enlace,raw):
    nombre=' '.join(nombre.split())
    if not 1<=len(nombre)<=100:raise ValueError('Escribe un nombre de conexión de hasta 100 caracteres.')
    sid=extraer_spreadsheet_id(enlace);info=validar_json(raw)
    with LOCK:
        data=leer()
        if any(c['hoja']==sid and c['correo']==info['client_email'] for c in data['cuentas']):raise ValueError('Esa cuenta y esa hoja ya están guardadas.')
        if len(data['cuentas'])>=20:raise ValueError('Puedes guardar hasta 20 conexiones.')
        meta=cliente(info).get(spreadsheetId=sid,fields='properties.title').execute()
        ident=uuid4().hex;folder=carpeta();folder.mkdir(parents=True,exist_ok=True)
        key=folder/(ident+'.json');key.write_text(json.dumps(info),encoding='utf-8')
        data['cuentas'].append(dict(id=ident,nombre=nombre,hoja=sid,correo=info['client_email'],titulo=meta['properties']['title']))
        try:guardar_store(data)
        except Exception:key.unlink(missing_ok=True);raise
    return ident

def listar():
    with LOCK:
        data=leer();return {'activa':data['activa'],'cuentas':[{**c,'enlace':'https://docs.google.com/spreadsheets/d/'+c['hoja']+'/edit'} for c in data['cuentas']]}

def actual():
    with LOCK:
        data=leer();return next((dict(c) for c in data['cuentas'] if c['id']==data['activa']),None)

def activar(ident):
    with LOCK:
        data=leer()
        if ident is not None and not any(c['id']==ident for c in data['cuentas']):raise ValueError('La conexión ya no existe.')
        data['activa']=ident;guardar_store(data)

def quitar(ident):
    with LOCK:
        data=leer();found=next((c for c in data['cuentas'] if c['id']==ident),None)
        if not found:raise ValueError('La conexión ya no existe.')
        data['cuentas']=[c for c in data['cuentas'] if c['id']!=ident]
        if data['activa']==ident:data['activa']=None
        guardar_store(data)
        # Solo se elimina el archivo con ID interno generado por el servidor.
        (carpeta()/(found['id']+'.json')).unlink(missing_ok=True)

def api_actual(config):
    return cliente(validar_json((carpeta()/(config['id']+'.json')).read_bytes()))

def importar_anterior():
    with LOCK:
        if (carpeta()/'conexiones.json').exists():return
        path=os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON','');sid=os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID','')
        if not path or not sid:return
        info=validar_json(Path(path).read_bytes());sid=extraer_spreadsheet_id(sid)
        ident=uuid4().hex;carpeta().mkdir(parents=True,exist_ok=True)
        (carpeta()/(ident+'.json')).write_text(json.dumps(info),encoding='utf-8')
        guardar_store({'activa':ident if os.getenv('GOOGLE_SHEETS_AUTO','').lower()=='true' else None,'cuentas':[dict(id=ident,nombre='ServiTech — Órdenes',hoja=sid,correo=info['client_email'],titulo='ServiTech — Órdenes')]})
