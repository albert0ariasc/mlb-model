from collections import Counter
from players import resolver_lineup
from simulate import correr

# ==========================================================
#  EDITA SOLO ESTA PARTE
# ==========================================================

EQUIPO_A = "Yankees"          # visitante
LINEUP_A = [
    "Aaron Judge",
    "Juan Soto",
    "Giancarlo Stanton",
    "Anthony Volpe",
    "Austin Wells",
    "Jazz Chisholm",
    "Ben Rice",
    "Trent Grisham",
    "Oswaldo Cabrera",
]
PITCHERS_A = ["Gerrit Cole", "Luke Weaver", "Clay Holmes"]

EQUIPO_B = "Tigers"           # local
LINEUP_B = [
    "Riley Greene",
    "Kerry Carpenter",
    "Spencer Torkelson",
    "Colt Keith",
    "Matt Vierling",
    "Jake Rogers",
    "Parker Meadows",
    "Zach McKinstry",
    "Javier Baez",
]
PITCHERS_B = ["Tarik Skubal", "Jason Foley", "Will Vest"]

PARK_HR = 1.00   # 1.00 = neutral, 1.30 = Coors, 0.85 = Oracle Park
SIMULACIONES = 10000

# ==========================================================


def main():
    print("Resolviendo jugadores...")
    la = resolver_lineup(LINEUP_A)
    pa = resolver_lineup(PITCHERS_A)
    lb = resolver_lineup(LINEUP_B)
    pb = resolver_lineup(PITCHERS_B)

    print(f"Simulando {SIMULACIONES:,} juegos...\n")
    r = correr(la, pa, lb, pb, PARK_HR, SIMULACIONES)

    print("=" * 46)
    print(f"  {EQUIPO_A}  @  {EQUIPO_B}")
    print("=" * 46)
    print(f"\n  {EQUIPO_A:12} {r['p_gana_a']:6.1%}   "
          f"{r['carreras_a']:.2f} carreras")
    print(f"  {EQUIPO_B:12} {r['p_gana_b']:6.1%}   "
          f"{r['carreras_b']:.2f} carreras")

    print(f"\n  Total esperado: {r['total_prom']:.2f}")
    print(f"  Rango probable: {r['total_p25']:.0f} - {r['total_p75']:.0f}")

    marcadores = Counter(r['resultados'])
    print("\n  Marcadores mas probables:")
    for (a, b), c in marcadores.most_common(8):
        gana = EQUIPO_A if a > b else EQUIPO_B
        print(f"    {a}-{b}   {c/SIMULACIONES:5.1%}   ({gana})")

    dist = Counter(a + b for a, b in r['resultados'])
    print("\n  Distribucion de carreras totales:")
    mx = max(dist.values())
    for t in range(0, 18):
        n = dist.get(t, 0)
        barra = "#" * int(n / mx * 32)
        print(f"    {t:2}  {barra} {n/SIMULACIONES:5.1%}")


if __name__ == "__main__":
    main()