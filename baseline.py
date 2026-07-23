import requests
from datetime import date, timedelta

BASE = "https://statsapi.mlb.com/api/v1"
hasta = date.today() - timedelta(days=1)
desde = hasta - timedelta(days=14)

r = requests.get(f"{BASE}/schedule", params={
    "sportId": 1, "startDate": desde.isoformat(),
    "endDate": hasta.isoformat(), "hydrate": "team",
}, timeout=30)

local = tot = 0
for d in r.json().get("dates", []):
    for g in d.get("games", []):
        if g.get("status", {}).get("abstractGameState") != "Final":
            continue
        a = g["teams"]["away"].get("score")
        h = g["teams"]["home"].get("score")
        if a is None or h is None:
            continue
        tot += 1
        if h > a:
            local += 1

print(f"{tot} juegos")
print(f"Gana el local: {local}/{tot} = {local/tot:.1%}")
print(f"\nSi tu modelo acierta 53%, contra este baseline "
      f"{'gana' if 0.53 > local/tot else 'pierde'} "
      f"{abs(0.53 - local/tot)*100:.1f} puntos")