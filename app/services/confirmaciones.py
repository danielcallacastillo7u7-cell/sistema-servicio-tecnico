from urllib.parse import quote
from fastapi.responses import RedirectResponse

def redireccion_confirmada(url, mensaje):
    respuesta = RedirectResponse(url=url, status_code=303)
    respuesta.set_cookie("servitech_exito", quote(mensaje, safe=""), max_age=60, samesite="lax", path="/")
    return respuesta
