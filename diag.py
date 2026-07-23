from collections import Counter
import random
from players import resolver_lineup
from simulate import precalcular, simular_mitad, elegir

LINEUP = ["Aaron Judge", "Juan Soto", "Giancarlo Stanton", "Anthony Volpe",
          "Austin Wells", "Jazz Chisholm", "Ben Rice", "Trent Grisham",
          "Oswaldo Cabrera"]
PITCHERS = ["Tarik Skubal"]

lin = resolver_lineup(LINEUP)
pit = resolver_lineup(PITCHERS)
tabla = precalcular(lin, pit, 1.0)

# 1. ¿Las probabilidades de un turno suman 1?
print("--- Suma de probabilidades por bateador ---")
for i, b in enumerate(lin):
    s = sum(tabla[i][0].values())
    print(f"  {b['name_full']:22} {s:.4f}")

# 2. ¿Qué eventos salen en 100k turnos?
print("\n--- Frecuencia de eventos simulados (bateador 1) ---")
c = Counter(elegir(tabla[0][0]) for _ in range(100000))
for ev, n in c.most_common():
    esperado = tabla[0][0].get(ev, 0)
    print(f"  {ev:14} simulado {n/100000:6.2%}   esperado {esperado:6.2%}")

# 3. Distribución de carreras por entrada
print("\n--- Carreras por media entrada (50k) ---")
d = Counter(simular_mitad(tabla, random.randint(0,8), 1, 1)[0]
            for _ in range(50000))
for k in sorted(d):
    print(f"  {k} carreras: {d[k]/50000:6.2%}")