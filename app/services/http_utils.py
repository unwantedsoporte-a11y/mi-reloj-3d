"""Utilidades HTTP compartidas por los clientes de CEX / Vinted / Wallapop.

Estas webs no ofrecen una API pública oficial y documentada: usamos los
mismos endpoints JSON que usan sus propias webs/apps (ingeniería inversa
"suave", muy habitual en herramientas de comparación de precios). Pueden
cambiar sin aviso, así que todo el parseo es defensivo: si algo falla,
se registra el error y se sigue con lo demás en vez de reventar el escaneo.
"""
import logging
import time

import requests

from app import config

logger = logging.getLogger("flipgames.http")

_session = None


def get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        })
        _session = s
    return _session


def polite_sleep():
    time.sleep(config.REQUEST_DELAY)


def dig(obj, *path, default=None):
    """Navega un dict/list anidado con una ruta de claves/índices, devolviendo
    `default` si cualquier paso no existe en vez de lanzar KeyError/TypeError."""
    cur = obj
    for step in path:
        try:
            cur = cur[step]
        except (KeyError, IndexError, TypeError):
            return default
    return cur if cur is not None else default


def find_first_matching_key(obj, needle: str):
    """Busca recursivamente en un dict/list la primera clave cuyo nombre
    contenga `needle` (case-insensitive) y devuelve su valor. Sirve de red
    de seguridad cuando el nombre exacto del campo cambia entre versiones
    de la API."""
    needle = needle.lower()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if needle in k.lower() and isinstance(v, (int, float)):
                return v
        for v in obj.values():
            found = find_first_matching_key(v, needle)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_first_matching_key(item, needle)
            if found is not None:
                return found
    return None
