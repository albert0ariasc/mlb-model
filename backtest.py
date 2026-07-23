import requests
from datetime import date, timedelta
from collections import defaultdict
from players import por_id
from simulate import correr
from schedule import PARK_HR

BASE = "https://statsapi.mlb.com/api/v1"


def juegos_terminados(desde, hasta):
    r = requests.get(f"{BASE}/schedule", params={
        "sportId": 1, "startDate": desde, "endDate": hasta,
        "hydrate": "team,venue,linescore",
    }, timeout=30)
    out = []
    for d in r.json().get("dates", []):
        for g in d.get("games", []):
            if g.get("status", {}).get("abstractGameState") != "Final":
                continue
            ls = g.get("linescore", {})
            out.append({
                "pk": g["gamePk"],
                "estadio": g.get("venue", {}).get("name", ""),
                "away": g["teams"]["away"]["team"]["name"],
                "home": g["teams"]["home"]["team"]["name"],
                "r_away": g["teams"]["away"].get("score"),
                "r_home": g["teams"]["home"].get("score"),
                "h_away": ls.get("teams", {}).get("away", {}).get("hits"),
                "h_home": ls.get("teams", {}).get("home", {}).get("hits"),
            })
    return out


def ids_reales(pk):
    """Devuelve los mlbam_id de bateadores y pitchers que jugaron."""
    r = requests.get(
        f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live", timeout=30)
    box = r.json().get("liveData", {}).get("boxscore", {}).get("teams", {})
    out = {}
    for lado in ("away", "home"):
        t = box.get(lado, {})
        out[lado] = {
            "bateadores": list(t.get("battingOrder", []))[:9],
            "pitchers": list(t.get("pitchers", [])),
        }
    return out


def resolver_ids(ids):
    out = []
    for i in ids:
        try:
            out.append(por_id(i))
        except ValueError:
            pass
    return out


def correr_backtest(dias=21, n_sims=2000, max_juegos=120):
    hasta = date.today() - timedelta(days=1)
    desde = hasta - timedelta(days=dias)
    juegos = juegos_terminados(desde.isoformat(), hasta.isoformat())
    juegos = juegos[:max_juegos]
    print(f"{len(juegos)} juegos a evaluar\n")

    filas = []
    saltados = 0
    for i, g in enumerate(juegos, 1):
        try:
            al = ids_reales(g["pk"])
            la = resolver_ids(al["away"]["bateadores"])
            pa = resolver_ids(al["away"]["pitchers"])
            lb = resolver_ids(al["home"]["bateadores"])
            pb = resolver_ids(al["home"]["pitchers"])

            if len(la) < 9 or len(lb) < 9 or not pa or not pb:
                saltados += 1
                continue

            r = correr(la, pa, lb, pb,
                       PARK_HR.get(g["estadio"], 1.0), n_sims)

            real_tot = g["r_away"] + g["r_home"]
            real_hits = (g["h_away"] or 0) + (g["h_home"] or 0)

            filas.append({
                "p_away": r["p_gana_a"],
                "gano_away": g["r_away"] > g["r_home"],
                "pred_tot": r["total_prom"],
                "real_tot": real_tot,
                "pred_hits": r["hits_prom"],
                "real_hits": real_hits,
                "over75": next(x["over"] for x in r["mercado_carreras"]
                               if x["linea"] == 7.5),
                "real_over75": real_tot > 7.5,
                "n_pit_a": len(pa), "n_pit_b": len(pb),
            })
            print(f"  {i}/{len(juegos)}  {g['away'][:16]:16} @ "
                  f"{g['home'][:16]:16}  pred {r['total_prom']:5.1f} / "
                  f"real {real_tot:2}")
        except Exception as e:
            saltados += 1
            print(f"  {i}/{len(juegos)}  saltado ({type(e).__name__})")

    print(f"\nSaltados: {saltados}")
    analizar(filas)


def analizar(f):
    if not f:
        print("Sin datos.")
        return
    n = len(f)
    print("\n" + "=" * 54)
    print(f"RESULTADOS  ({n} juegos)")
    print("=" * 54)

    ok = sum(1 for x in f if (x["p_away"] > .5) == x["gano_away"])
    print(f"\nGanador acertado: {ok}/{n} = {ok/n:.1%}")

    err = sum(abs(x["pred_tot"] - x["real_tot"]) for x in f) / n
    sesgo = sum(x["pred_tot"] - x["real_tot"] for x in f) / n
    pred_prom = sum(x["pred_tot"] for x in f) / n
    real_prom = sum(x["real_tot"] for x in f) / n
    print(f"\nCarreras totales")
    print(f"  Modelo predice: {pred_prom:.2f}")
    print(f"  Realidad:       {real_prom:.2f}")
    print(f"  Error promedio: {err:.2f}")
    print(f"  Sesgo:          {sesgo:+.2f}")

    err_h = sum(abs(x["pred_hits"] - x["real_hits"]) for x in f) / n
    sesgo_h = sum(x["pred_hits"] - x["real_hits"] for x in f) / n
    ph = sum(x["pred_hits"] for x in f) / n
    rh = sum(x["real_hits"] for x in f) / n
    print(f"\nHits totales")
    print(f"  Modelo predice: {ph:.2f}")
    print(f"  Realidad:       {rh:.2f}")
    print(f"  Error promedio: {err_h:.2f}")
    print(f"  Sesgo:          {sesgo_h:+.2f}")

    print(f"\nPitchers por juego (promedio): "
          f"{sum(x['n_pit_a']+x['n_pit_b'] for x in f)/n/2:.1f} por equipo")

    print(f"\nCalibración (over 7.5)")
    cubos = defaultdict(list)
    for x in f:
        cubos[int(x["over75"] * 10)].append(x["real_over75"])
    for k in sorted(cubos):
        v = cubos[k]
        print(f"  Modelo dice {k*10}-{k*10+10}%: "
              f"real {sum(v)/len(v):5.1%}  (n={len(v)})")

    brier = sum((x["p_away"] - (1 if x["gano_away"] else 0)) ** 2
                for x in f) / n
    print(f"\nBrier score: {brier:.4f}  (0.25 = moneda al aire)")


if __name__ == "__main__":
    correr_backtest()