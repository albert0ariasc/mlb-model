import pandas as pd
from datetime import date
from pybaseball import statcast, playerid_reverse_lookup
from db import get_conn

SEASON_START = "2026-03-26"

EVENT_MAP = {
    'strikeout': 'K', 'strikeout_double_play': 'K',
    'walk': 'BB', 'intent_walk': 'BB',
    'hit_by_pitch': 'HBP',
    'single': '1B', 'double': '2B', 'triple': '3B', 'home_run': 'HR',
}

def clasificar(ev):
    return EVENT_MAP.get(ev, 'OUT' if pd.notna(ev) else None)

def fetch_season(start=SEASON_START, end=None):
    end = end or date.today().isoformat()
    print(f"Descargando Statcast {start} -> {end}...")
    df = statcast(start_dt=start, end_dt=end)
    df = df[df['events'].notna()].copy()
    df['ev'] = df['events'].apply(clasificar)
    return df[df['ev'].notna()]

def calc_rates(group):
    n = len(group)
    if n == 0:
        return None
    counts = group['ev'].value_counts()
    return {
        'pa': n,
        'k_rate': counts.get('K', 0) / n,
        'bb_rate': counts.get('BB', 0) / n,
        'hbp_rate': counts.get('HBP', 0) / n,
        'single_rate': counts.get('1B', 0) / n,
        'double_rate': counts.get('2B', 0) / n,
        'triple_rate': counts.get('3B', 0) / n,
        'hr_rate': counts.get('HR', 0) / n,
    }

def build_stats(df, id_col, hand_col, table):
    as_of = date.today().isoformat()
    rows = []
    for split_name, mask in [
        ('all', pd.Series(True, index=df.index)),
        ('vs_L', df[hand_col] == 'L'),
        ('vs_R', df[hand_col] == 'R'),
    ]:
        sub = df[mask]
        for pid, g in sub.groupby(id_col):
            r = calc_rates(g)
            if r:
                rows.append({'mlbam_id': int(pid), 'as_of': as_of,
                             'split': split_name, **r})

    out = pd.DataFrame(rows)
    if table == 'pitcher_stats':
        out = out.rename(columns={'pa': 'bf'})

    with get_conn() as conn:
        conn.execute(f"DELETE FROM {table} WHERE as_of = ?", (as_of,))
        out.to_sql(table, conn, if_exists='append', index=False)
    print(f"{table}: {len(out)} filas")
    return out

def build_league_baseline(df):
    as_of = date.today().isoformat()
    rows = []
    for split_name, mask in [
        ('all', pd.Series(True, index=df.index)),
        ('vs_L', df['p_throws'] == 'L'),
        ('vs_R', df['p_throws'] == 'R'),
    ]:
        r = calc_rates(df[mask])
        rows.append({'as_of': as_of, 'split': split_name,
                     **{k: v for k, v in r.items() if k != 'pa'}})
    with get_conn() as conn:
        conn.execute("DELETE FROM league_baseline WHERE as_of = ?", (as_of,))
        pd.DataFrame(rows).to_sql('league_baseline', conn,
                                  if_exists='append', index=False)
    print("league_baseline: ok")

def sync_players(df):
    ids = pd.concat([df['batter'], df['pitcher']]).unique().tolist()
    info = playerid_reverse_lookup(ids, key_type='mlbam')
    info['name_full'] = (info['name_first'].str.title() + ' '
                         + info['name_last'].str.title())
    info['name_search'] = (info['name_full'].str.normalize('NFKD')
                           .str.encode('ascii', 'ignore').str.decode('ascii')
                           .str.lower())
    out = info[['key_mlbam', 'name_full', 'name_search']].rename(
        columns={'key_mlbam': 'mlbam_id'})

    hands = pd.concat([
        df[['batter', 'stand']].rename(columns={'batter': 'mlbam_id', 'stand': 'bats'}),
        df[['pitcher', 'p_throws']].rename(columns={'pitcher': 'mlbam_id', 'p_throws': 'throws'}),
    ]).groupby('mlbam_id').first().reset_index()

    out = out.merge(hands, on='mlbam_id', how='left')
    with get_conn() as conn:
        out.to_sql('players', conn, if_exists='replace', index=False)
    print(f"players: {len(out)} jugadores")

def update_all():
    df = fetch_season()
    print(f"Turnos al bat procesados: {len(df):,}")
    sync_players(df)
    build_stats(df, 'batter', 'p_throws', 'batter_stats')
    build_stats(df, 'pitcher', 'stand', 'pitcher_stats')
    build_league_baseline(df)
    print("Listo.")

if __name__ == "__main__":
    update_all()