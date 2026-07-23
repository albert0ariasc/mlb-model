import random
from matchup import enfrentamiento

HITS = ('single_rate', 'double_rate', 'triple_rate', 'hr_rate')


def avanzar(bases, outs, evento):
    b1, b2, b3 = bases

    if evento == 'k_rate':
        return (b1, b2, b3), outs + 1, 0

    if evento == 'out_rate':
        if outs < 2 and b3 and random.random() < 0.30:
            return (b1, b2, False), outs + 1, 1
        return (b1, b2, b3), outs + 1, 0

    if evento in ('bb_rate', 'hbp_rate'):
        if not b1:
            return (True, b2, b3), outs, 0
        if not b2:
            return (True, True, b3), outs, 0
        if not b3:
            return (True, True, True), outs, 0
        return (True, True, True), outs, 1

    if evento == 'single_rate':
        r = int(b3) + int(b2)
        if b1 and random.random() < 0.30:
            return (True, False, True), outs, r
        return (True, bool(b1), False), outs, r

    if evento == 'double_rate':
        r = int(b3) + int(b2)
        if b1:
            if random.random() < 0.45:
                return (False, True, False), outs, r + 1
            return (False, True, True), outs, r
        return (False, True, False), outs, r

    if evento == 'triple_rate':
        return (False, False, True), outs, int(b1) + int(b2) + int(b3)

    if evento == 'hr_rate':
        return (False, False, False), outs, 1 + int(b1) + int(b2) + int(b3)

    return (b1, b2, b3), outs + 1, 0


def elegir(probs):
    x = random.random()
    acc = 0
    for ev, p in probs.items():
        acc += p
        if x < acc:
            return ev
    return 'out_rate'


def precalcular(lineup, pitchers, park_hr):
    tabla = []
    for bat in lineup:
        fila = []
        for pit in pitchers:
            probs, _, _ = enfrentamiento(
                bat['mlbam_id'], bat['bats'],
                pit['mlbam_id'], pit['throws'], park_hr)
            fila.append(probs)
        tabla.append(fila)
    return tabla


def pitcher_activo(inning, n_pitchers):
    if inning <= 6 or n_pitchers == 1:
        return 0
    return min(1 + (inning - 7), n_pitchers - 1)


def simular_mitad(tabla, orden_inicio, inning, n_pitchers, box=None):
    bases, outs, carreras, hits = (False, False, False), 0, 0, 0
    i = orden_inicio
    pit_idx = pitcher_activo(inning, n_pitchers)

    while outs < 3:
        slot = i % 9
        ev = elegir(tabla[slot][pit_idx])
        if ev in HITS:
            hits += 1
        if box is not None:
            box[slot][ev] = box[slot].get(ev, 0) + 1
        bases, outs, r = avanzar(bases, outs, ev)
        carreras += r
        i += 1

    return carreras, hits, i % 9


def simular_juego(tabla_a, tabla_b, n_pit_a, n_pit_b, box_a=None, box_b=None):
    ra = rb = ha = hb = 0
    oa = ob = 0

    for inning in range(1, 10):
        r, h, oa = simular_mitad(tabla_a, oa, inning, n_pit_b, box_a)
        ra += r; ha += h
        if inning == 9 and rb > ra:
            break
        r, h, ob = simular_mitad(tabla_b, ob, inning, n_pit_a, box_b)
        rb += r; hb += h

    inning = 10
    while ra == rb and inning < 18:
        r, h, oa = simular_mitad(tabla_a, oa, inning, n_pit_b, box_a)
        ra += r; ha += h
        r, h, ob = simular_mitad(tabla_b, ob, inning, n_pit_a, box_b)
        rb += r; hb += h
        inning += 1

    return ra, rb, ha, hb


def a_momio(p):
    """Probabilidad -> momio americano justo (sin comisión)."""
    if p <= 0 or p >= 1:
        return None
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def correr(lineup_a, pitchers_a, lineup_b, pitchers_b,
           park_hr=1.0, n=10000,
           lineas_carreras=(7.5, 8.5, 9.5),
           lineas_hits=(12.5, 13.5, 14.5, 15.5),
           handicaps=(1.5,)):

    tabla_a = precalcular(lineup_a, pitchers_b, park_hr)
    tabla_b = precalcular(lineup_b, pitchers_a, park_hr)

    box_a = [dict() for _ in range(9)]
    box_b = [dict() for _ in range(9)]

    res = [simular_juego(tabla_a, tabla_b, len(pitchers_a), len(pitchers_b),
                         box_a, box_b) for _ in range(n)]

    ra = [x[0] for x in res]
    rb = [x[1] for x in res]
    tot = [a + b for a, b in zip(ra, rb)]
    hits_tot = [x[2] + x[3] for x in res]

    p_a = sum(1 for a, b in zip(ra, rb) if a > b) / n
    p_b = sum(1 for a, b in zip(ra, rb) if b > a) / n

    # Totales de carreras
    mercado_carreras = []
    for L in lineas_carreras:
        over = sum(1 for t in tot if t > L) / n
        mercado_carreras.append({
            'linea': L, 'over': over, 'under': 1 - over,
            'momio_over': a_momio(over), 'momio_under': a_momio(1 - over),
        })

    # Totales de hits
    mercado_hits = []
    for L in lineas_hits:
        over = sum(1 for h in hits_tot if h > L) / n
        mercado_hits.append({
            'linea': L, 'over': over, 'under': 1 - over,
            'momio_over': a_momio(over), 'momio_under': a_momio(1 - over),
        })

    # Hándicap (run line)
    mercado_hcp = []
    for H in handicaps:
        a_cubre = sum(1 for a, b in zip(ra, rb) if a - b > -H) / n
        b_cubre = sum(1 for a, b in zip(ra, rb) if b - a > -H) / n
        a_menos = sum(1 for a, b in zip(ra, rb) if a - b > H) / n
        b_menos = sum(1 for a, b in zip(ra, rb) if b - a > H) / n
        mercado_hcp.append({
            'linea': H,
            'a_mas': a_cubre, 'b_mas': b_cubre,
            'a_menos': a_menos, 'b_menos': b_menos,
            'momio_a_mas': a_momio(a_cubre), 'momio_b_mas': a_momio(b_cubre),
            'momio_a_menos': a_momio(a_menos), 'momio_b_menos': a_momio(b_menos),
        })

    # Ganador + total combinado
    combinados = []
    for L in lineas_carreras:
        for eq, gana in (('a', True), ('b', False)):
            for lado in ('over', 'under'):
                c = sum(1 for a, b, t in zip(ra, rb, tot)
                        if ((a > b) == gana) and
                           ((t > L) if lado == 'over' else (t < L)))
                p = c / n
                combinados.append({
                    'equipo': eq, 'linea': L, 'lado': lado,
                    'p': p, 'momio': a_momio(p),
                })

    # Props por bateador
    props = []
    for tabla, box, eq in ((tabla_a, box_a, 'a'), (tabla_b, box_b, 'b')):
        for slot in range(9):
            d = box[slot]
            pa_tot = sum(d.values())
            if pa_tot == 0:
                continue
            h = sum(d.get(e, 0) for e in HITS)
            props.append({
                'equipo': eq, 'slot': slot + 1,
                'pa_prom': pa_tot / n,
                'hits_prom': h / n,
                'hr_prom': d.get('hr_rate', 0) / n,
                'k_prom': d.get('k_rate', 0) / n,
            })

    return {
        'p_gana_a': p_a, 'p_gana_b': p_b,
        'momio_a': a_momio(p_a), 'momio_b': a_momio(p_b),
        'carreras_a': sum(ra) / n, 'carreras_b': sum(rb) / n,
        'total_prom': sum(tot) / n,
        'hits_a': sum(x[2] for x in res) / n,
        'hits_b': sum(x[3] for x in res) / n,
        'hits_prom': sum(hits_tot) / n,
        'total_p25': sorted(tot)[int(n * .25)],
        'total_p75': sorted(tot)[int(n * .75)],
        'mercado_carreras': mercado_carreras,
        'mercado_hits': mercado_hits,
        'mercado_handicap': mercado_hcp,
        'combinados': combinados,
        'props': props,
        'resultados': [(a, b) for a, b in zip(ra, rb)],
        'hits_totales': hits_tot,
    }