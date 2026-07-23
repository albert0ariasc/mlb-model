import requests
from datetime import date, timedelta
from players import buscar
from simulate import correr
from schedule import PARK_HR

BASE = "https://statsapi.mlb.com/api/v1"

def suave(ns):
    out = []
    for n in ns:
        try: out.append(buscar(n))
        except ValueError: pass
    return out

hasta = date.today() - timedelta(days=1)
desde = hasta - timedelta(days=5)
r = requests.get(f"{BASE}/schedule", params={
    "sportId": 1, "startDate": desde.isoformat(),
    "endDate": hasta.isoformat(), "hydrate": "team,venue"}, timeout=30)

juegos = []
for d in r.json().get("dates", []):
    for g in d.get("games", []):
        if g.get("status", {}).get("abstractGameState") == "Final":
            juegos.append(g)

for g in juegos[:5]:
    pk = g["gamePk"]
    fl = requests.get(
        f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live", timeout=30)
    box = fl.json()["liveData"]["boxscore"]["teams"]
    la = suave([box["away"]["players"][f"ID{p}"]["person"]["fullName"]
                for p in box["away"].get("battingOrder", [])[:9]])
    pa = suave([box["away"]["players"][f"ID{p}"]["person"]["fullName"]
                for p in box["away"].get("pitchers", [])])
    lb = suave([box["home"]["players"][f"ID{p}"]["person"]["fullName"]
                for p in box["home"].get("battingOrder", [])[:9]])
    pb = suave([box["home"]["players"][f"ID{p}"]["person"]["fullName"]
                for p in box["home"].get("pitchers", [])])

    if len(la) < 9 or len(lb) < 9 or not pa or not pb:
        print("saltado"); continue

    park = PARK_HR.get(g.get("venue", {}).get("name", ""), 1.0)
    res = correr(la, pa, lb, pb, park, 3000)
    real = g["teams"]["away"]["score"] + g["teams"]["home"]["score"]

    print(f"\n{g['teams']['away']['team']['name']} @ "
          f"{g['teams']['home']['team']['name']}")
    print(f"  pitchers usados: away={len(pa)} home={len(pb)}")
    print(f"  park_hr: {park}")
    print(f"  modelo: {res['total_prom']:.2f}   real: {real}")
    print(f"  hits modelo: {res['hits_prom']:.2f}")