import sys
import requests
from datetime import date
from players import por_id, buscar
from simulate import correr
from schedule import juegos_del_dia, PARK_HR
from predicciones import guardar

BASE = "https://statsapi.mlb.com/api/v1"
N_SIMS = 8000


def roster_activo(team_id):
    """Bateadores del roster activo, para armar un lineup aproximado."""
    r = requests.get(f"{BASE}/teams/{team_id}/roster",
                     params={"rosterType": "active"}, timeout=20).json()
    return [p["person"]["id"] for p in r.get("roster", [])
            if p.get("position", {}).get("type") != "Pitcher"]


def lineup_confirmado(pk, lado):
    try:
        r = requests.get(
            f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live",
            timeout=20).json()
        t = r["liveData"]["boxscore"]["teams"][lado]
        return list(t.get("battingOrder", []))[:9]
    except Exception:
        return []


def res_ids(ids):
    out = []
    for i in ids:
        try:
            out.append(por_id(i))
        except ValueError:
            pass
    return out


def main(fecha=None):
    fecha = fecha or date.today().isoformat()
    js = juegos_del_dia(fecha)
    print(f"{len(js)} juegos el {fecha}\n")

    sched = requests.get(f"{BASE}/schedule", params={
        "sportId": 1, "date": fecha, "hydrate": "team,probablePitcher"
    }, timeout=20).json()
    team_ids = {}
    for d in sched.get("dates", []):
        for g in d.get("games", []):
            team_ids[g["gamePk"]] = (
                g["teams"]["away"]["team"]["id"],
                g["teams"]["home"]["team"]["id"])

    for j in js:
        pk = j["game_pk"]
        pa_n, pb_n = j["away"]["pitcher"], j["home"]["pitcher"]
        if not pa_n or not pb_n:
            print(f"  {j['away']['nombre']} @ {j['home']['nombre']}: "
                  f"sin abridores anunciados\n")
            continue

        try:
            pa = [buscar(pa_n)]
            pb = [buscar(pb_n)]
        except ValueError as e:
            print(f"  {j['away']['nombre']} @ {j['home']['nombre']}: {e}\n")
            continue

        la_ids = lineup_confirmado(pk, "away")
        lb_ids = lineup_confirmado(pk, "home")
        conf = len(la_ids) == 9 and len(lb_ids) == 9

        if not conf:
            ta, tb = team_ids.get(pk, (None, None))
            if not ta:
                continue
            la_ids = roster_activo(ta)[:9]
            lb_ids = roster_activo(tb)[:9]

        la, lb = res_ids(la_ids), res_ids(lb_ids)
        if len(la) < 9 or len(lb) < 9:
            print(f"  {j['away']['nombre']} @ {j['home']['nombre']}: "
                  f"lineup incompleto ({len(la)}/{len(lb)})\n")
            continue

        r = correr(la, pa, lb, pb, j["park_hr"], N_SIMS)

        marca = "✓" if conf else "~"
        print(f"{marca} {j['away']['nombre']} @ {j['home']['nombre']}")
        print(f"   {pa_n} vs {pb_n}   [{j['estadio']}]")
        print(f"   Gana visitante: {r['p_gana_a']:.1%}   "
              f"({r['carreras_a']:.2f} - {r['carreras_b']:.2f})")
        print(f"   Total: {r['total_prom']:.2f}   Hits: {r['hits_prom']:.2f}")
        for x in r["mercado_carreras"]:
            print(f"     O/U {x['linea']}: over {x['over']:.1%} "
                  f"({x['momio_over']:+d})")
        print()

        guardar(pk, fecha, j["away"]["nombre"], j["home"]["nombre"],
                j["estadio"], pa_n, pb_n, r, N_SIMS)

    print("Predicciones guardadas. Mañana corre:")
    print("  python predicciones.py update")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)