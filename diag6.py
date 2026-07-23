from collections import defaultdict
import requests, json
from datetime import date, timedelta
from players import por_id
from simulate import correr
from schedule import PARK_HR

BASE = "https://statsapi.mlb.com/api/v1"

def ids(pk):
    r = requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live",
                     timeout=30).json()
    box = r["liveData"]["boxscore"]["teams"]
    return {l: {"bat": list(box[l].get("battingOrder", []))[:9],
                "pit": list(box[l].get("pitchers", []))} for l in ("away","home")}

def res(lst):
    o = []
    for i in lst:
        try: o.append(por_id(i))
        except ValueError: pass
    return o

hasta = date.today() - timedelta(days=1)
desde = hasta - timedelta(days=10)
sched = requests.get(f"{BASE}/schedule", params={
    "sportId":1, "startDate":desde.isoformat(), "endDate":hasta.isoformat(),
    "hydrate":"team,venue"}, timeout=30).json()

juegos = [g for d in sched.get("dates",[]) for g in d.get("games",[])
          if g.get("status",{}).get("abstractGameState")=="Final"][:40]

ok_todos = ok_solo1 = n = 0
for g in juegos:
    try:
        a = ids(g["gamePk"])
        la, pa = res(a["away"]["bat"]), res(a["away"]["pit"])
        lb, pb = res(a["home"]["bat"]), res(a["home"]["pit"])
        if len(la)<9 or len(lb)<9 or not pa or not pb: continue
        park = PARK_HR.get(g.get("venue",{}).get("name",""), 1.0)
        gano_a = g["teams"]["away"]["score"] > g["teams"]["home"]["score"]

        r1 = correr(la, pa, lb, pb, park, 1500)
        r2 = correr(la, pa[:1], lb, pb[:1], park, 1500)

        ok_todos += (r1["p_gana_a"] > .5) == gano_a
        ok_solo1 += (r2["p_gana_a"] > .5) == gano_a
        n += 1
        print(f"  {n}: todos {r1['p_gana_a']:.0%} / solo abridor {r2['p_gana_a']:.0%} / real {'A' if gano_a else 'B'}")
    except Exception as e:
        pass

print(f"\nCon TODOS los pitchers del boxscore: {ok_todos}/{n} = {ok_todos/n:.1%}")
print(f"Solo con el abridor:                 {ok_solo1}/{n} = {ok_solo1/n:.1%}")