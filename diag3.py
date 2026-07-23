import requests
from datetime import date, timedelta

BASE = "https://statsapi.mlb.com/api/v1"
hasta = date.today() - timedelta(days=1)
desde = hasta - timedelta(days=14)

r = requests.get(f"{BASE}/schedule", params={
    "sportId": 1, "startDate": desde.isoformat(),
    "endDate": hasta.isoformat(), "hydrate": "team",
}, timeout=30)

tot = n = 0
for d in r.json().get("dates", []):
    for g in d.get("games", []):
        if g.get("status", {}).get("abstractGameState") != "Final":
            continue
        a, h = g["teams"]["away"].get("score"), g["teams"]["home"].get("score")
        if a is None:
            continue
        tot += a + h
        n += 1

print(f"Últimas 2 semanas: {tot/n:.2f} carreras por juego ({n} juegos)")

from db import get_conn
with get_conn() as c:
    row = c.execute(
        "SELECT * FROM league_baseline WHERE split='all' "
        "ORDER BY as_of DESC LIMIT 1").fetchone()
    ev = sum(row[k] for k in ('single_rate','double_rate','triple_rate','hr_rate'))
    print(f"Tasa de hits en la base: {ev:.1%}")