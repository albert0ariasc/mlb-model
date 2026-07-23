from db import get_conn

EVENTOS = ['k_rate', 'bb_rate', 'hbp_rate', 'single_rate',
           'double_rate', 'triple_rate', 'hr_rate']

# Qué tan grande debe ser la muestra para confiar en ella
PESO_BAT = 200
PESO_PIT = 300


def _ultima_fecha(conn, tabla):
    return conn.execute(f"SELECT MAX(as_of) FROM {tabla}").fetchone()[0]


def liga(split='all'):
    with get_conn() as conn:
        f = _ultima_fecha(conn, 'league_baseline')
        r = conn.execute(
            "SELECT * FROM league_baseline WHERE as_of=? AND split=?",
            (f, split)).fetchone()
    return {e: r[e] for e in EVENTOS}


def _stats(mlbam_id, tabla, split, col_n, peso):
    """Trae las tasas del jugador ya suavizadas hacia la media de liga."""
    with get_conn() as conn:
        f = _ultima_fecha(conn, tabla)
        r = conn.execute(
            f"SELECT * FROM {tabla} WHERE mlbam_id=? AND as_of=? AND split=?",
            (mlbam_id, f, split)).fetchone()
        if r is None:
            r = conn.execute(
                f"SELECT * FROM {tabla} WHERE mlbam_id=? AND as_of=? AND split='all'",
                (mlbam_id, f)).fetchone()

    base = liga(split)
    if r is None:
        return base, 0

    n = r[col_n]
    w = n / (n + peso)          # 0 = confía en la liga, 1 = confía en el jugador
    return {e: w * r[e] + (1 - w) * base[e] for e in EVENTOS}, n


def stats_bateador(mlbam_id, mano_pitcher):
    split = 'vs_L' if mano_pitcher == 'L' else 'vs_R'
    return _stats(mlbam_id, 'batter_stats', split, 'pa', PESO_BAT)


def stats_pitcher(mlbam_id, mano_bateador):
    split = 'vs_L' if mano_bateador == 'L' else 'vs_R'
    return _stats(mlbam_id, 'pitcher_stats', split, 'bf', PESO_PIT)


def _odds(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return p / (1 - p)


def enfrentamiento(bat_id, bat_mano, pit_id, pit_mano, park_hr=1.0):
    """Devuelve la probabilidad de cada resultado posible del turno al bat."""
    b, n_b = stats_bateador(bat_id, pit_mano)
    p, n_p = stats_pitcher(pit_id, bat_mano)
    lg = liga('vs_L' if pit_mano == 'L' else 'vs_R')

    probs = {}
    for e in EVENTOS:
        o = _odds(b[e]) * _odds(p[e]) / _odds(lg[e])
        probs[e] = o / (1 + o)

    probs['hr_rate'] *= park_hr
    probs['double_rate'] *= (1 + (park_hr - 1) * 0.5)

    total = sum(probs.values())
    if total >= 1.0:
        probs = {k: v / total * 0.98 for k, v in probs.items()}
        total = 0.98
    probs['out_rate'] = 1 - total

    return probs, n_b, n_p