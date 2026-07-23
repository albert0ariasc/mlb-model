import requests
from datetime import date

BASE = "https://statsapi.mlb.com/api/v1"

# Factores de HR por estadio (aproximados, 1.00 = neutral)
PARK_HR = {
    "Coors Field": 1.28, "Great American Ball Park": 1.20,
    "Yankee Stadium": 1.18, "Citizens Bank Park": 1.14,
    "Globe Life Field": 1.10, "Fenway Park": 1.06,
    "Truist Park": 1.04, "Wrigley Field": 1.03,
    "Rogers Centre": 1.03, "Chase Field": 1.02,
    "Nationals Park": 1.01, "Dodger Stadium": 1.01,
    "Angel Stadium": 1.00, "Progressive Field": 1.00,
    "Busch Stadium": 0.97, "Target Field": 0.97,
    "Minute Maid Park": 0.96, "Daikin Park": 0.96,
    "Citi Field": 0.95, "Petco Park": 0.94,
    "Comerica Park": 0.93, "loanDepot park": 0.92,
    "Oracle Park": 0.88, "T-Mobile Park": 0.90,
    "Kauffman Stadium": 0.91, "PNC Park": 0.93,
    "Guaranteed Rate Field": 1.08, "Rate Field": 1.08,
    "American Family Field": 1.05, "Oriole Park at Camden Yards": 1.02,
    "Sutter Health Park": 1.00, "George M. Steinbrenner Field": 1.00,
}


def juegos_del_dia(fecha=None):
    """Lista los juegos de un día. fecha en formato YYYY-MM-DD."""
    fecha = fecha or date.today().isoformat()
    url = f"{BASE}/schedule"
    params = {
        "sportId": 1,
        "date": fecha,
        "hydrate": "probablePitcher,team,venue,linescore",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    juegos = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            venue = g.get("venue", {}).get("name", "")
            away = g["teams"]["away"]
            home = g["teams"]["home"]
            juegos.append({
                "game_pk": g["gamePk"],
                "hora": g.get("gameDate", ""),
                "estado": g.get("status", {}).get("detailedState", ""),
                "estadio": venue,
                "park_hr": PARK_HR.get(venue, 1.00),
                "away": {
                    "nombre": away["team"]["name"],
                    "abbr": away["team"].get("abbreviation", ""),
                    "pitcher": (away.get("probablePitcher") or {}).get("fullName"),
                },
                "home": {
                    "nombre": home["team"]["name"],
                    "abbr": home["team"].get("abbreviation", ""),
                    "pitcher": (home.get("probablePitcher") or {}).get("fullName"),
                },
            })
    return juegos


def lineups(game_pk):
    """Lineups confirmados. Se publican ~2-3 hrs antes del juego."""
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    box = r.json().get("liveData", {}).get("boxscore", {}).get("teams", {})

    out = {}
    for lado in ("away", "home"):
        t = box.get(lado, {})
        jugadores = t.get("players", {})
        orden = t.get("battingOrder", [])
        bateadores = []
        for pid in orden[:9]:
            p = jugadores.get(f"ID{pid}", {})
            n = p.get("person", {}).get("fullName")
            if n:
                bateadores.append(n)
        bullpen = []
        for pid in t.get("bullpen", []):
            p = jugadores.get(f"ID{pid}", {})
            n = p.get("person", {}).get("fullName")
            if n:
                bullpen.append(n)
        out[lado] = {"lineup": bateadores, "bullpen": bullpen}
    return out


if __name__ == "__main__":
    import sys
    f = sys.argv[1] if len(sys.argv) > 1 else None
    js = juegos_del_dia(f)
    print(f"{len(js)} juegos\n")
    for j in js:
        print(f"[{j['game_pk']}] {j['away']['nombre']} @ {j['home']['nombre']}")
        print(f"    {j['estadio']}  (HR factor {j['park_hr']})")
        print(f"    {j['away']['pitcher'] or '?'} vs {j['home']['pitcher'] or '?'}")
        print(f"    {j['estado']}\n")