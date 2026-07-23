import sqlite3
from datetime import date
from pathlib import Path

DB = Path(__file__).parent / "data" / "predicciones.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS predicciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_pk     INTEGER,
    fecha_juego TEXT,
    fecha_pred  TEXT,
    away        TEXT,
    home        TEXT,
    estadio     TEXT,
    abridor_a   TEXT,
    abridor_b   TEXT,
    p_gana_a    REAL,
    carreras_a  REAL,
    carreras_b  REAL,
    total_pred  REAL,
    hits_pred   REAL,
    over_75     REAL,
    over_85     REAL,
    over_95     REAL,
    hits_o125   REAL,
    hits_o135   REAL,
    n_sims      INTEGER,
    version     TEXT,
    -- se llenan después
    r_away      INTEGER,
    r_home      INTEGER,
    h_away      INTEGER,
    h_home      INTEGER,
    UNIQUE(game_pk, version)
);
"""

VERSION = "v1"


def conn():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def guardar(game_pk, fecha_juego, away, home, estadio,
            abridor_a, abridor_b, r, n_sims):
    def linea(mercado, L):
        for x in r[mercado]:
            if x["linea"] == L:
                return x["over"]
        return None

    with conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO predicciones
            (game_pk, fecha_juego, fecha_pred, away, home, estadio,
             abridor_a, abridor_b, p_gana_a, carreras_a, carreras_b,
             total_pred, hits_pred, over_75, over_85, over_95,
             hits_o125, hits_o135, n_sims, version)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (game_pk, fecha_juego, date.today().isoformat(),
              away, home, estadio, abridor_a, abridor_b,
              r["p_gana_a"], r["carreras_a"], r["carreras_b"],
              r["total_prom"], r["hits_prom"],
              linea("mercado_carreras", 7.5),
              linea("mercado_carreras", 8.5),
              linea("mercado_carreras", 9.5),
              linea("mercado_hits", 12.5),
              linea("mercado_hits", 13.5),
              n_sims, VERSION))


def actualizar_resultados():
    """Baja los marcadores de los juegos ya terminados."""
    import requests
    with conn() as c:
        pend = c.execute(
            "SELECT DISTINCT game_pk FROM predicciones WHERE r_away IS NULL"
        ).fetchall()

    n = 0
    for row in pend:
        pk = row["game_pk"]
        try:
            r = requests.get(
                f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live",
                timeout=20).json()
            ls = r["liveData"]["linescore"]
            if r["gameData"]["status"]["abstractGameState"] != "Final":
                continue
            t = ls["teams"]
            with conn() as c:
                c.execute("""UPDATE predicciones SET r_away=?, r_home=?,
                             h_away=?, h_home=? WHERE game_pk=?""",
                          (t["away"]["runs"], t["home"]["runs"],
                           t["away"].get("hits"), t["home"].get("hits"), pk))
            n += 1
        except Exception:
            pass
    print(f"{n} resultados actualizados")


def reporte():
    with conn() as c:
        f = c.execute(
            "SELECT * FROM predicciones WHERE r_away IS NOT NULL"
        ).fetchall()

    if not f:
        print("Sin resultados todavía.")
        return

    n = len(f)
    print(f"\n{'='*54}\nREGISTRO  ({n} juegos con resultado)\n{'='*54}")

    ok = sum(1 for x in f if (x["p_gana_a"] > .5) == (x["r_away"] > x["r_home"]))
    print(f"\nGanador: {ok}/{n} = {ok/n:.1%}")

    local = sum(1 for x in f if x["r_home"] > x["r_away"])
    print(f"Baseline (gana local): {local/n:.1%}")

    tot_r = [x["r_away"] + x["r_home"] for x in f]
    tot_p = [x["total_pred"] for x in f]
    err = sum(abs(a - b) for a, b in zip(tot_p, tot_r)) / n
    sesgo = sum(a - b for a, b in zip(tot_p, tot_r)) / n
    print(f"\nCarreras  pred {sum(tot_p)/n:.2f} / real {sum(tot_r)/n:.2f}")
    print(f"  error {err:.2f}   sesgo {sesgo:+.2f}")

    print(f"\nCalibración over 7.5:")
    from collections import defaultdict
    cub = defaultdict(list)
    for x in f:
        if x["over_75"] is not None:
            cub[int(x["over_75"] * 10)].append(
                (x["r_away"] + x["r_home"]) > 7.5)
    for k in sorted(cub):
        v = cub[k]
        print(f"  {k*10}-{k*10+10}%: real {sum(v)/len(v):5.1%}  (n={len(v)})")

    brier = sum((x["p_gana_a"] - (1 if x["r_away"] > x["r_home"] else 0))**2
                for x in f) / n
    print(f"\nBrier: {brier:.4f}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        actualizar_resultados()
    reporte()