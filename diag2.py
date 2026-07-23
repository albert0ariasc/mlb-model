from collections import Counter
from players import resolver_lineup
from simulate import precalcular, simular_mitad

LINEUP = ["Aaron Judge", "Juan Soto", "Giancarlo Stanton", "Anthony Volpe",
          "Austin Wells", "Jazz Chisholm", "Ben Rice", "Trent Grisham",
          "Oswaldo Cabrera"]

lin = resolver_lineup(LINEUP)
pit = resolver_lineup(["Tarik Skubal"])
tabla = precalcular(lin, pit, 1.0)

N = 50000
carreras = Counter()
bateadores = []

for _ in range(N):
    r, h, fin = simular_mitad(tabla, 0, 1, 1)
    carreras[r] += 1
    bateadores.append(fin if fin > 0 else 9)

print("Carreras por media entrada:")
print(f"{'car':>4} {'modelo':>8} {'MLB real':>9}")
real = {0: .724, 1: .146, 2: .070, 3: .033, 4: .015, 5: .007}
for k in sorted(carreras):
    r = real.get(k, .005)
    print(f"{k:>4} {carreras[k]/N:>8.1%} {r:>9.1%}")

prom_bat = sum(bateadores) / N
print(f"\nBateadores por entrada: {prom_bat:.2f}")
print(f"MLB real:               ~4.25")
print(f"\nCarreras/entrada modelo: {sum(k*v for k,v in carreras.items())/N:.3f}")
print(f"MLB real:                ~0.52")