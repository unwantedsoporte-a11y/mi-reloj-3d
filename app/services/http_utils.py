"""Utilidades compartidas por los clientes de CEX / Vinted / Wallapop para
parsear las respuestas JSON de forma defensiva: estas webs no ofrecen una
API pública documentada, así que si algo cambia de nombre o desaparece,
estas funciones devuelven `default` en vez de reventar el escaneo.
"""


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
