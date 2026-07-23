from players import buscar
from matchup import enfrentamiento

BAT = "Aaron Judge"
PIT = "Tarik Skubal"

b = buscar(BAT)
p = buscar(PIT)

probs, n_b, n_p = enfrentamiento(
    b['mlbam_id'], b['bats'],
    p['mlbam_id'], p['throws']
)

print(f"{b['name_full']} ({b['bats']}, {n_b} PA)  vs  "
      f"{p['name_full']} ({p['throws']}, {n_p} BF)\n")

nombres = {
    'k_rate': 'Ponche', 'bb_rate': 'Base por bolas', 'hbp_rate': 'Golpeado',
    'single_rate': 'Sencillo', 'double_rate': 'Doble', 'triple_rate': 'Triple',
    'hr_rate': 'Home run', 'out_rate': 'Out en juego',
}

for k, v in sorted(probs.items(), key=lambda x: -x[1]):
    print(f"  {nombres[k]:16} {v:6.1%}")

print(f"\n  Suma: {sum(probs.values()):.1%}  (debe ser 100%)")