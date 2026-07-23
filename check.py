from db import get_conn
from players import buscar

with get_conn() as conn:
    for t in ['players', 'batter_stats', 'pitcher_stats', 'league_baseline']:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}: {n} filas")

    print("\n--- Liga (vs pitcher derecho) ---")
    r = conn.execute("""
        SELECT k_rate, bb_rate, single_rate, hr_rate
        FROM league_baseline WHERE split='vs_R'
        ORDER BY as_of DESC LIMIT 1
    """).fetchone()
    if r:
        print(f"K%:  {r['k_rate']:.1%}")
        print(f"BB%: {r['bb_rate']:.1%}")
        print(f"1B%: {r['single_rate']:.1%}")
        print(f"HR%: {r['hr_rate']:.1%}")

print("\n--- Prueba de nombre ---")
p = buscar("Aaron Judge")
print(p['name_full'], "| batea:", p['bats'], "| id:", p['mlbam_id'])

with get_conn() as conn:
    print("\n--- Sus splits ---")
    for r in conn.execute("""
        SELECT split, pa, k_rate, bb_rate, hr_rate
        FROM batter_stats WHERE mlbam_id=?
        ORDER BY as_of DESC, split
    """, (p['mlbam_id'],)).fetchall()[:3]:
        print(f"{r['split']:5} PA:{r['pa']:4}  K:{r['k_rate']:.1%}  "
              f"BB:{r['bb_rate']:.1%}  HR:{r['hr_rate']:.1%}")