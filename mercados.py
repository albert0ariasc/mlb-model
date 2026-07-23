from players import resolver_lineup
from simulate import correr
from juego import (LINEUP_A, PITCHERS_A, LINEUP_B, PITCHERS_B,
                   EQUIPO_A, EQUIPO_B, PARK_HR)

la = resolver_lineup(LINEUP_A); pa = resolver_lineup(PITCHERS_A)
lb = resolver_lineup(LINEUP_B); pb = resolver_lineup(PITCHERS_B)

r = correr(la, pa, lb, pb, PARK_HR, 20000)

def m(x):
    return f"{x:+d}" if x else "—"

print(f"\n{EQUIPO_A} @ {EQUIPO_B}\n" + "=" * 52)
print(f"\nGANADOR")
print(f"  {EQUIPO_A:14} {r['p_gana_a']:6.1%}   {m(r['momio_a'])}")
print(f"  {EQUIPO_B:14} {r['p_gana_b']:6.1%}   {m(r['momio_b'])}")

print(f"\nTOTALES DE CARRERAS   (esperado {r['total_prom']:.2f})")
for x in r['mercado_carreras']:
    print(f"  Más de {x['linea']:<5} {x['over']:6.1%} {m(x['momio_over']):>7}"
          f"     Menos {x['under']:6.1%} {m(x['momio_under']):>7}")

print(f"\nTOTALES DE HITS   (esperado {r['hits_prom']:.2f})")
for x in r['mercado_hits']:
    print(f"  Más de {x['linea']:<5} {x['over']:6.1%} {m(x['momio_over']):>7}"
          f"     Menos {x['under']:6.1%} {m(x['momio_under']):>7}")

print(f"\nHÁNDICAP")
for x in r['mercado_handicap']:
    print(f"  {EQUIPO_A} +{x['linea']}: {x['a_mas']:6.1%} {m(x['momio_a_mas']):>7}"
          f"     {EQUIPO_A} -{x['linea']}: {x['a_menos']:6.1%} {m(x['momio_a_menos']):>7}")
    print(f"  {EQUIPO_B} +{x['linea']}: {x['b_mas']:6.1%} {m(x['momio_b_mas']):>7}"
          f"     {EQUIPO_B} -{x['linea']}: {x['b_menos']:6.1%} {m(x['momio_b_menos']):>7}")

print(f"\nGANADOR & TOTAL")
nom = {'a': EQUIPO_A, 'b': EQUIPO_B}
for c in r['combinados']:
    lado = 'más de' if c['lado'] == 'over' else 'menos de'
    print(f"  {nom[c['equipo']]} y {lado} {c['linea']:<5} "
          f"{c['p']:6.1%}   {m(c['momio'])}")