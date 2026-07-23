import sys
import json
import os
import requests
from datetime import date, datetime, timezone, timedelta
from players import por_id, buscar
from simulate import correr
from schedule import juegos_del_dia
from predicciones import guardar

BASE = "https://statsapi.mlb.com/api/v1"
N = 6000
VENTANA_HORAS = 4          # solo re-simula juegos que empiezan dentro de esto
SALIDA = "docs"
ESTADO = os.path.join(SALIDA, "estado.json")


def ahora():
    return datetime.now(timezone.utc)


def parse_hora(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def lineup(pk, lado):
    try:
        r = requests.get(
            f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live",
            timeout=25).json()
        return list(r["liveData"]["boxscore"]["teams"][lado]
                    .get("battingOrder", []))[:9]
    except Exception:
        return []


def roster(tid):
    try:
        r = requests.get(f"{BASE}/teams/{tid}/roster",
                         params={"rosterType": "active"}, timeout=25).json()
        return [p["person"]["id"] for p in r.get("roster", [])
                if p.get("position", {}).get("type") != "Pitcher"]
    except Exception:
        return []


def res(ids):
    o = []
    for i in ids:
        try:
            o.append(por_id(i))
        except ValueError:
            pass
    return o


def cargar_estado():
    if os.path.exists(ESTADO):
        try:
            with open(ESTADO) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def main(fecha=None):
    fecha = fecha or date.today().isoformat()
    os.makedirs(SALIDA, exist_ok=True)

    prev = cargar_estado()
    if prev.get("fecha") != fecha:
        prev = {"fecha": fecha, "juegos": {}}

    js = juegos_del_dia(fecha)
    print(f"{len(js)} juegos el {fecha}")

    sched = requests.get(f"{BASE}/schedule", params={
        "sportId": 1, "date": fecha, "hydrate": "team"}, timeout=25).json()
    tid = {}
    for d in sched.get("dates", []):
        for g in d.get("games", []):
            tid[g["gamePk"]] = (g["teams"]["away"]["team"]["id"],
                                g["teams"]["home"]["team"]["id"])

    guardados = prev.get("juegos", {})
    out = []
    t0 = ahora()

    for k, j in enumerate(js, 1):
        pk = str(j["game_pk"])
        pan, pbn = j["away"]["pitcher"], j["home"]["pitcher"]
        etiqueta = f"{j['away']['nombre']} @ {j['home']['nombre']}"
        hora = parse_hora(j.get("hora", ""))
        viejo = guardados.get(pk)

        # ¿ya empezó? conserva lo último que teníamos
        empezado = j["estado"] not in ("Scheduled", "Pre-Game", "Warmup")
        if empezado and viejo:
            viejo["congelado"] = True
            out.append(viejo)
            print(f"  [{k}] {etiqueta} — en curso, congelado")
            continue

        # ¿está fuera de la ventana? conserva si ya lo teníamos
        fuera = hora and (hora - t0) > timedelta(hours=VENTANA_HORAS)
        if fuera and viejo:
            out.append(viejo)
            print(f"  [{k}] {etiqueta} — fuera de ventana, sin cambios")
            continue

        if not pan or not pbn:
            print(f"  [{k}] {etiqueta} — sin abridores")
            if viejo:
                out.append(viejo)
            continue

        try:
            pa, pb = [buscar(pan)], [buscar(pbn)]
        except ValueError:
            print(f"  [{k}] {etiqueta} — abridor no encontrado")
            if viejo:
                out.append(viejo)
            continue

        lai, lbi = lineup(pk, "away"), lineup(pk, "home")
        conf = len(lai) == 9 and len(lbi) == 9
        if not conf:
            ta, tb = tid.get(int(pk), (None, None))
            if not ta:
                continue
            lai, lbi = roster(ta)[:9], roster(tb)[:9]

        la, lb = res(lai), res(lbi)
        if len(la) < 9 or len(lb) < 9:
            print(f"  [{k}] {etiqueta} — lineup incompleto")
            if viejo:
                out.append(viejo)
            continue

        # ¿cambió algo respecto a la corrida anterior?
        cambios = []
        if viejo:
            if viejo.get("abridor_a") != pan:
                cambios.append(f"abridor {j['away']['nombre']}: "
                               f"{viejo.get('abridor_a')} → {pan}")
            if viejo.get("abridor_b") != pbn:
                cambios.append(f"abridor {j['home']['nombre']}: "
                               f"{viejo.get('abridor_b')} → {pbn}")
            if not viejo.get("conf") and conf:
                cambios.append("lineups confirmados")

        r = correr(la, pa, lb, pb, j["park_hr"], N)
        guardar(int(pk), fecha, j["away"]["nombre"], j["home"]["nombre"],
                j["estadio"], pan, pbn, r, N)

        out.append({
            "pk": pk, "away": j["away"]["nombre"], "home": j["home"]["nombre"],
            "abridor_a": pan, "abridor_b": pbn, "hora": j.get("hora", ""),
            "estadio": j["estadio"], "park": j["park_hr"], "conf": conf,
            "actualizado": t0.isoformat(), "cambios": cambios,
            "estado": j["estado"], "congelado": False,
            "pa": r["p_gana_a"], "pb": r["p_gana_b"],
            "ma": r["momio_a"], "mb": r["momio_b"],
            "ca": r["carreras_a"], "cb": r["carreras_b"],
            "tot": r["total_prom"], "hits": r["hits_prom"],
            "mc": r["mercado_carreras"], "mh": r["mercado_hits"],
            "hcp": r["mercado_handicap"], "comb": r["combinados"],
            "la": [x["name_full"] for x in la],
            "lb": [x["name_full"] for x in lb],
        })
        marca = "★" if cambios else ("✓" if conf else "~")
        print(f"  [{k}] {marca} {etiqueta} → {r['p_gana_a']:.0%} / "
              f"{r['total_prom']:.1f}" +
              (f"  CAMBIOS: {'; '.join(cambios)}" if cambios else ""))

    # ordena por hora
    out.sort(key=lambda x: x.get("hora", ""))

    with open(ESTADO, "w") as f:
        json.dump({"fecha": fecha,
                   "juegos": {g["pk"]: g for g in out if g.get("pk")}}, f)

    html = (PLANTILLA
            .replace("__FECHA__", fecha)
            .replace("__ACTUALIZADO__", t0.strftime("%Y-%m-%d %H:%M UTC"))
            .replace("__DATOS__", json.dumps(out, ensure_ascii=False)))

    with open(os.path.join(SALIDA, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nGenerado: {SALIDA}/index.html")


PLANTILLA = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MLB __FECHA__</title><style>
:root{--bg:#0d0f13;--p:#151920;--l:#232935;--t:#e8eaef;--d:#7f8899;
--ok:#4ade80;--b:#60a5fa;--w:#fbbf24;--r:#f87171}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--t);
font:14px/1.55 ui-monospace,Menlo,monospace;padding:26px 16px}
.w{max-width:1060px;margin:0 auto}
header{margin-bottom:20px}
h1{font-size:15px;letter-spacing:.06em;text-transform:uppercase;margin:0}
.sub{font-size:11px;color:var(--d);margin-top:4px}
.g{background:var(--p);border:1px solid var(--l);border-radius:10px;
padding:16px;margin-bottom:14px}
.g.frz{opacity:.5}
.hd{display:flex;justify-content:space-between;align-items:baseline;
padding:10px 0;border-bottom:1px solid var(--l)}
.nm{font-size:15px}.pc{font-size:21px;font-weight:600}.win{color:var(--ok)}
h2{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--d);
margin:20px 0 8px;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:12px}
td{padding:5px 3px;border-bottom:1px solid #1b202a}td.r{text-align:right}
.mo{color:var(--b)}.d{color:var(--d)}.s{font-size:11px}
.c{display:inline-block;padding:2px 7px;border-radius:4px;font-size:10px;
text-transform:uppercase;margin-right:5px}
.c.ok{background:#14301f;color:var(--ok)}
.c.wr{background:#332512;color:var(--w)}
.c.ch{background:#3a1c1e;color:var(--r)}
.gr{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:740px){.gr{grid-template-columns:1fr}}
details summary{cursor:pointer;color:var(--d);font-size:11px;
text-transform:uppercase;letter-spacing:.08em;margin-top:16px}
</style></head><body><div class="w">
<header><h1>MLB — __FECHA__</h1>
<div class="sub">Última actualización: __ACTUALIZADO__ ·
se regenera cada hora</div></header>
<div id="o"></div></div>
<script>
const D=__DATOS__;
const p=x=>(x*100).toFixed(1)+"%";
const m=x=>x==null?"—":(x>0?"+"+x:""+x);
const hl=s=>{try{return new Date(s).toLocaleTimeString([],
{hour:'2-digit',minute:'2-digit'})}catch(e){return""}};
document.getElementById("o").innerHTML=D.map(g=>{
const a=g.pa>g.pb, nm={a:g.away,b:g.home};
return `<div class="g${g.congelado?' frz':''}">
<div>${(g.cambios||[]).length?`<span class="c ch">cambió</span>`:''}
<span class="c ${g.conf?'ok':'wr'}">${g.conf?'lineup confirmado':'roster estimado'}</span>
<span class="d s">${hl(g.hora)} · ${g.estadio} · HR ${g.park}
${g.congelado?' · EN CURSO':''}</span></div>
${(g.cambios||[]).length?`<div class="s" style="color:var(--r);margin-top:6px">
${g.cambios.join(" · ")}</div>`:''}
<div class="hd"><span class="nm ${a?'win':''}">${g.away}
<span class="d s"> ${g.abridor_a}</span></span>
<span><span class="d s">${g.ca.toFixed(2)}</span>
<span class="pc ${a?'win':''}"> ${p(g.pa)}</span>
<span class="mo"> ${m(g.ma)}</span></span></div>
<div class="hd"><span class="nm ${!a?'win':''}">${g.home}
<span class="d s"> ${g.abridor_b}</span></span>
<span><span class="d s">${g.cb.toFixed(2)}</span>
<span class="pc ${!a?'win':''}"> ${p(g.pb)}</span>
<span class="mo"> ${m(g.mb)}</span></span></div>
<div class="gr" style="margin-top:18px"><div>
<h2>Carreras · esperado ${g.tot.toFixed(2)}</h2><table>
${g.mc.map(x=>`<tr><td>${x.linea}</td>
<td class="r">Más ${p(x.over)} <span class="mo">${m(x.momio_over)}</span></td>
<td class="r">Menos ${p(x.under)} <span class="mo">${m(x.momio_under)}</span></td>
</tr>`).join("")}</table>
<h2>Hits · esperado ${g.hits.toFixed(2)}</h2><table>
${g.mh.map(x=>`<tr><td>${x.linea}</td>
<td class="r">Más ${p(x.over)} <span class="mo">${m(x.momio_over)}</span></td>
<td class="r">Menos ${p(x.under)} <span class="mo">${m(x.momio_under)}</span></td>
</tr>`).join("")}</table>
<h2>Hándicap</h2><table>${g.hcp.map(x=>`
<tr><td>${g.away} +${x.linea}</td><td class="r">${p(x.a_mas)} <span class="mo">${m(x.momio_a_mas)}</span></td></tr>
<tr><td>${g.away} −${x.linea}</td><td class="r">${p(x.a_menos)} <span class="mo">${m(x.momio_a_menos)}</span></td></tr>
<tr><td>${g.home} +${x.linea}</td><td class="r">${p(x.b_mas)} <span class="mo">${m(x.momio_b_mas)}</span></td></tr>
<tr><td>${g.home} −${x.linea}</td><td class="r">${p(x.b_menos)} <span class="mo">${m(x.momio_b_menos)}</span></td></tr>
`).join("")}</table></div>
<div><h2>Ganador &amp; total</h2><table>
${g.comb.map(c=>`<tr><td class="s">${nm[c.equipo]} y ${c.lado=='over'?'más':'menos'} de ${c.linea}</td>
<td class="r">${p(c.p)} <span class="mo">${m(c.momio)}</span></td></tr>`).join("")}
</table>
<details><summary>Lineups</summary>
<div class="gr s d" style="margin-top:8px">
<div>${g.la.map((n,i)=>`${i+1}. ${n}`).join("<br>")}</div>
<div>${g.lb.map((n,i)=>`${i+1}. ${n}`).join("<br>")}</div>
</div></details></div></div></div>`}).join("");
</script></body></html>"""


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)