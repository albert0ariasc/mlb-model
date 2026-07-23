import requests
from datetime import date, timedelta
from players import buscar, por_id

BASE = "https://statsapi.mlb.com/api/v1"
hasta = date.today() - timedelta(days=1)
desde = hasta - timedelta(days=3)
r = requests.get(f"{BASE}/schedule", params={
    "sportId": 1, "startDate": desde.isoformat(),
    "endDate": hasta.isoformat(), "hydrate": "team"}, timeout=30)

fallan_nombre = {}
fallan_id = []
total = 0

for d in r.json().get("dates", []):
    for g in d.get("games", [])[:8]:
        if g.get("status", {}).get("abstractGameState") != "Final":
            continue
        pk = g["gamePk"]
        fl = requests.get(
            f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live",
            timeout=30).json()
        box = fl["liveData"]["boxscore"]["teams"]
        for lado in ("away", "home"):
            t = box[lado]
            ids = list(t.get("battingOrder", [])[:9]) + list(t.get("pitchers", []))
            for pid in ids:
                total += 1
                n = t["players"].get(f"ID{pid}", {}).get("person", {}).get("fullName", "?")
                try:
                    por_id(pid)
                except ValueError:
                    fallan_id.append(f"{n} ({pid})")
                try:
                    buscar(n)
                except ValueError as e:
                    fallan_nombre[n] = str(e)[:55]

print(f"Total de jugadores revisados: {total}\n")
print(f"Fallan por NOMBRE: {len(fallan_nombre)}")
for n, e in sorted(fallan_nombre.items()):
    print(f"  {n:26} {e}")
print(f"\nFallan por ID: {len(fallan_id)}")
for x in sorted(set(fallan_id)):
    print(f"  {x}")