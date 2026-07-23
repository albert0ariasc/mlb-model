import re
import unicodedata
from db import get_conn

SUFIJOS = r'\s+(jr|sr|ii|iii|iv|v)\.?$'


def normalizar(s):
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('ascii')
    s = s.lower().strip()
    s = s.replace('.', '')
    s = re.sub(r'\s+', ' ', s)
    return s


def variantes(nombre):
    base = normalizar(nombre)
    v = [base]
    sin_sufijo = re.sub(SUFIJOS, '', base).strip()
    if sin_sufijo != base:
        v.append(sin_sufijo)
    partes = sin_sufijo.split()
    if len(partes) >= 2:
        v.append(partes[-1])
    return v


def por_id(mlbam_id):
    with get_conn() as conn:
        r = conn.execute(
            "SELECT * FROM players WHERE mlbam_id=?", (int(mlbam_id),)
        ).fetchone()
    if r:
        return dict(r)
    raise ValueError(f"ID no encontrado: {mlbam_id}")


def buscar(nombre):
    with get_conn() as conn:
        for q in variantes(nombre):
            exacto = conn.execute(
                "SELECT * FROM players WHERE name_search = ?", (q,)).fetchall()
            if len(exacto) == 1:
                return dict(exacto[0])
            if len(exacto) > 1:
                nombres = ", ".join(r['name_full'] for r in exacto[:8])
                raise ValueError(f"Ambiguo '{nombre}' -> {nombres}")

            parcial = conn.execute(
                "SELECT * FROM players WHERE name_search LIKE ?",
                (f"%{q}%",)).fetchall()
            if len(parcial) == 1:
                return dict(parcial[0])
            if len(parcial) > 1:
                nombres = ", ".join(r['name_full'] for r in parcial[:8])
                raise ValueError(f"Ambiguo '{nombre}' -> {nombres}")

    raise ValueError(f"No encontrado: {nombre}")


def resolver_lineup(nombres):
    ok, fallos = [], []
    for n in nombres:
        try:
            ok.append(buscar(n))
        except ValueError as e:
            fallos.append(str(e))
    if fallos:
        raise ValueError("Problemas con estos nombres:\n  - " +
                         "\n  - ".join(fallos))
    return ok
