from flask import Flask, render_template, request, jsonify
from collections import Counter
import requests
from datetime import date

from players import por_id, buscar
from simulate import correr
from schedule import juegos_del_dia, PARK_HR
from predicciones import guardar, actualizar_resultados, conn

app = Flask(__name__)
BASE = "https://statsapi.mlb.com/api/v1"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/juegos")
def api_juegos():
    f = request.args.get("fecha") or date.today().isoformat()
    try:
        return jsonify({"fecha": f, "juegos": juegos_del_dia(f)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _lineup(pk, lado):
    try:
        r = requests.get(
            f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live",
            timeout=20).json()
        t = r["liveData"]["boxscore"]["teams"][lado]
        return list(t.get("battingOrder", []))[:9]
    except Exception:
        return []


def _roster(team_id):
    r = requests.get(f"{BASE}/teams/{team_id}/roster",
                     params={"rosterType": "active"}, timeout=20).json()
    return [p["person"]["id"] for p in r.get("roster", [])
            if p.get("position", {}).get("type") != "Pitcher"]


def _res(ids):
    out = []
    for i in ids:
        try:
            out.append(por_id(i))
        except ValueError:
            pass
    return out


@app.route("/api/simular_juego", methods=["POST"])
def api_simular_juego():
    d = request.json
    pk = d["game_pk"]
    n = int(d.get("n", 8000))

    js = juegos_del_dia(d["fecha"])
    j = next((x for x in js if x["game_pk"] == pk), None)
    if not j:
        return jsonify({"error": "Juego no encontrado"}), 404

    if not j["away"]["pitcher"] or not j["home"]["pitcher"]:
        return jsonify({"error": "Abridores no anunciados todavía"}), 400

    try:
        pa = [buscar(j["away"]["pitcher"])]
        pb = [buscar(j["home"]["pitcher"])]
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    la_ids = _lineup(pk, "away")
    lb_ids = _lineup(pk, "home")
    confirmado = len(la_ids) == 9 and len(lb_ids) == 9

    if not confirmado:
        sched = requests.get(f"{BASE}/schedule", params={
            "sportId": 1, "date": d["fecha"], "hydrate": "team"}, timeout=20).json()
        tid = {}
        for dd in sched.get("dates", []):
            for g in dd.get("games", []):
                tid[g["gamePk"]] = (g["teams"]["away"]["team"]["id"],
                                    g["teams"]["home"]["team"]["id"])
        ta, tb = tid.get(pk, (None, None))
        if not ta:
            return jsonify({"error": "No se pudo armar el lineup"}), 400
        la_ids, lb_ids = _roster(ta)[:9], _roster(tb)[:9]

    la, lb = _res(la_ids), _res(lb_ids)
    if len(la) < 9 or len(lb) < 9:
        return jsonify({"error": f"Lineup incompleto ({len(la)}/{len(lb)})"}), 400

    r = correr(la, pa, lb, pb, j["park_hr"], n)

    guardar(pk, d["fecha"], j["away"]["nombre"], j["home"]["nombre"],
            j["estadio"], j["away"]["pitcher"], j["home"]["pitcher"], r, n)

    dist = Counter(a + b for a, b in r["resultados"])
    marc = Counter(r["resultados"]).most_common(8)
    N = len(r["resultados"])

    return jsonify({
        "away": j["away"]["nombre"], "home": j["home"]["nombre"],
        "abridor_a": j["away"]["pitcher"], "abridor_b": j["home"]["pitcher"],
        "estadio": j["estadio"], "park_hr": j["park_hr"],
        "confirmado": confirmado,
        "lineup_a": [x["name_full"] for x in la],
        "lineup_b": [x["name_full"] for x in lb],
        "p_gana_a": r["p_gana_a"], "p_gana_b": r["p_gana_b"],
        "momio_a": r["momio_a"], "momio_b": r["momio_b"],
        "carreras_a": r["carreras_a"], "carreras_b": r["carreras_b"],
        "total_prom": r["total_prom"], "hits_prom": r["hits_prom"],
        "hits_a": r["hits_a"], "hits_b": r["hits_b"],
        "mercado_carreras": r["mercado_carreras"],
        "mercado_hits": r["mercado_hits"],
        "mercado_handicap": r["mercado_handicap"],
        "combinados": r["combinados"],
        "marcadores": [{"a": a, "b": b, "p": c / N} for (a, b), c in marc],
        "dist": [{"t": t, "p": dist.get(t, 0) / N} for t in range(1, 20)],
    })


@app.route("/api/registro")
def api_registro():
    with conn() as c:
        f = c.execute("SELECT * FROM predicciones "
                      "WHERE r_away IS NOT NULL "
                      "ORDER BY fecha_juego DESC").fetchall()
        pend = c.execute("SELECT COUNT(*) FROM predicciones "
                         "WHERE r_away IS NULL").fetchone()[0]

    if not f:
        return jsonify({"n": 0, "pendientes": pend})

    n = len(f)
    ok = sum(1 for x in f if (x["p_gana_a"] > .5) == (x["r_away"] > x["r_home"]))
    local = sum(1 for x in f if x["r_home"] > x["r_away"])
    tot_r = [x["r_away"] + x["r_home"] for x in f]
    tot_p = [x["total_pred"] for x in f]

    from collections import defaultdict
    cub = defaultdict(list)
    for x in f:
        if x["over_75"] is not None:
            cub[int(x["over_75"] * 10)].append((x["r_away"] + x["r_home"]) > 7.5)

    brier = sum((x["p_gana_a"] - (1 if x["r_away"] > x["r_home"] else 0))**2
                for x in f) / n

    return jsonify({
        "n": n, "pendientes": pend,
        "acierto": ok / n, "baseline": local / n,
        "pred_prom": sum(tot_p) / n, "real_prom": sum(tot_r) / n,
        "error": sum(abs(a-b) for a, b in zip(tot_p, tot_r)) / n,
        "sesgo": sum(a-b for a, b in zip(tot_p, tot_r)) / n,
        "brier": brier,
        "calibracion": [{"rango": f"{k*10}-{k*10+10}%",
                         "real": sum(v)/len(v), "n": len(v)}
                        for k, v in sorted(cub.items())],
        "ultimos": [{
            "fecha": x["fecha_juego"], "away": x["away"], "home": x["home"],
            "p": x["p_gana_a"], "pred": x["total_pred"],
            "real": x["r_away"] + x["r_home"],
            "marcador": f"{x['r_away']}-{x['r_home']}",
            "ok": (x["p_gana_a"] > .5) == (x["r_away"] > x["r_home"]),
        } for x in f[:25]],
    })


@app.route("/api/actualizar", methods=["POST"])
def api_actualizar():
    actualizar_resultados()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)