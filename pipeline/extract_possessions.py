#!/usr/bin/env python3
"""
Stap 2a: Extraheer en filter alle Barcelona-possessions uit de StatsBomb data.
Eénmalige run — output dient als cache voor score_attacks.py.

Run: source venv/bin/activate && python extract_possessions.py
"""

import ujson as json
from pathlib import Path
from collections import defaultdict

# ── Paden ──────────────────────────────────────────────────────────────────────
DATA_ROOT     = Path(__file__).parent.parent / "data" / "statsbomb-open-data" / "data"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(exist_ok=True)

# ── Constanten / filter-parameters ────────────────────────────────────────────
BARCA_TEAM_NAME  = "Barcelona"
MESSI_NAME       = "Lionel Andrés Messi Cuccittini"
MIN_EVENTS       = 4
MIN_XG           = 0.05     # minimum xG voor kwalificerend schot
MIN_PROGRESSION  = 30.0     # meters bal-progressie op 120m-veld

LA_LIGA_CID = 11
# La Liga season_ids Messi-era (2004/05 t/m 2020/21) — 1973/74 (278) bewust weggelaten
MESSI_ERA_SEASON_IDS = {37, 38, 39, 40, 41, 21, 22, 23, 24, 25, 26, 27, 2, 1, 4, 42, 90}

# Top-level event-keys die we bewaren (strip rommel als `counterpress`, `out`, etc.)
KEEP_EVENT_KEYS = {
    "id", "index", "period", "timestamp", "minute", "second",
    "type", "player", "position", "location", "duration",
    "related_events", "possession", "possession_team", "play_pattern", "team",
    "pass", "carry", "dribble", "shot", "ball_receipt",
    "interception", "ball_recovery", "clearance", "goalkeeper",
}


# ── Kleine helpers ─────────────────────────────────────────────────────────────

def load_json(path: Path):
    with open(path, "rb") as f:
        return json.load(f)


def type_name(event: dict) -> str:
    t = event.get("type")
    return t["name"] if isinstance(t, dict) else ""


def player_name(event: dict) -> str:
    p = event.get("player")
    return p["name"] if isinstance(p, dict) else ""


def location_x(event: dict):
    loc = event.get("location")
    return loc[0] if loc else None


def shot_info(event: dict):
    """Return (xg: float|None, outcome: str|None) voor een Shot-event."""
    shot = event.get("shot")
    if not shot:
        return None, None
    xg = shot.get("statsbomb_xg")
    outcome = (shot.get("outcome") or {}).get("name")
    return xg, outcome


def ts_to_seconds(ts: str) -> float:
    """'HH:MM:SS.mmm' → seconden (float)."""
    try:
        h, m, rest = ts.split(":")
        return int(h) * 3600 + int(m) * 60 + float(rest)
    except Exception:
        return 0.0


def trim_event(event: dict) -> dict:
    out = {k: v for k, v in event.items() if k in KEEP_EVENT_KEYS}
    # under_pressure is een sparse boolean: aanwezig = True, ontbreekt ≠ False
    out["under_pressure"] = "under_pressure" in event
    return out


# ── Possession-verwerking ──────────────────────────────────────────────────────

def build_record(match_meta: dict, possession_id: int, events: list) -> dict:
    """Bouw één possession-record op vanuit de raw event-lijst."""
    events = sorted(events, key=lambda e: e.get("index", 0))

    shot_events = [e for e in events if type_name(e) == "Shot"]

    # Start-x: eerste event met locatie
    start_x = next((location_x(e) for e in events if location_x(e) is not None), None)

    # End-x: locatie van het schot (als er één is), anders laatste locatie
    end_x = None
    if shot_events:
        end_x = location_x(shot_events[-1])
    if end_x is None:
        end_x = next((location_x(e) for e in reversed(events) if location_x(e) is not None), None)

    # Freeze-frame: eerste schot met freeze_frame
    freeze_frame  = None
    shot_location = None
    for se in shot_events:
        ff = (se.get("shot") or {}).get("freeze_frame")
        if ff:
            freeze_frame  = ff
            shot_location = se.get("location")
            break

    # Tijdsduur (binnen de helft — vergelijk timestamps alleen binnen zelfde period)
    duration_seconds = 0.0
    by_period = defaultdict(list)
    for e in events:
        if "timestamp" in e:
            by_period[e.get("period", 1)].append(ts_to_seconds(e["timestamp"]))
    for times in by_period.values():
        if len(times) >= 2:
            duration_seconds += max(times) - min(times)

    # xG en outcome van het (eerste kwalificerende) schot
    xg, outcome = None, None
    for se in shot_events:
        xg, outcome = shot_info(se)
        if outcome == "Goal" or (xg is not None and xg >= MIN_XG):
            break

    return {
        **match_meta,
        "possession_id":    possession_id,
        "minute":           events[0].get("minute", 0),
        "duration_seconds": round(duration_seconds, 3),
        "num_events":       len(events),
        "start_x":          round(start_x, 1) if start_x is not None else None,
        "end_x":            round(end_x,   1) if end_x   is not None else None,
        "xg":               round(xg, 4) if xg is not None else None,
        "shot_outcome":     outcome,
        "shot_location":    shot_location,
        "has_freeze_frame": freeze_frame is not None,
        "freeze_frame":     freeze_frame,
        "events":           [trim_event(e) for e in events],
    }


def process_match(match_meta: dict, event_file: Path) -> tuple[list, dict]:
    """Verwerk één match-bestand. Return (possessions, step_counts)."""
    events = load_json(event_file)

    # Groepeer op possession_id
    by_possession = defaultdict(list)
    for e in events:
        pid = e.get("possession")
        if pid is not None:
            by_possession[pid].append(e)

    counts = {k: 0 for k in ("total", "barca", "min_events", "messi", "shot", "progression")}
    results = []

    for pid, evs in by_possession.items():
        counts["total"] += 1

        # 1. Barcelona-bezit
        pteam = (evs[0].get("possession_team") or {}).get("name", "")
        if pteam != BARCA_TEAM_NAME:
            continue
        counts["barca"] += 1

        # 2. Minimaal aantal events
        if len(evs) < MIN_EVENTS:
            continue
        counts["min_events"] += 1

        # 3. Minstens één Messi-event
        if not any(player_name(e) == MESSI_NAME for e in evs):
            continue
        counts["messi"] += 1

        # 4. Schot met xG >= MIN_XG of doelpunt
        shot_evs = [e for e in evs if type_name(e) == "Shot"]
        qualifying = False
        for se in shot_evs:
            xg, outcome = shot_info(se)
            if outcome == "Goal" or (xg is not None and xg >= MIN_XG):
                qualifying = True
                break
        if not qualifying:
            continue
        counts["shot"] += 1

        # 5. Progressie >= MIN_PROGRESSION (start_x → end_x van het schot)
        evs_sorted = sorted(evs, key=lambda e: e.get("index", 0))
        start_x = next((location_x(e) for e in evs_sorted if location_x(e) is not None), None)
        end_x   = location_x(shot_evs[-1]) if shot_evs else None
        if end_x is None:
            end_x = next((location_x(e) for e in reversed(evs_sorted) if location_x(e) is not None), None)

        if start_x is None or end_x is None or (end_x - start_x) < MIN_PROGRESSION:
            continue
        counts["progression"] += 1

        results.append(build_record(match_meta, pid, evs))

    return results, counts


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    competitions = load_json(DATA_ROOT / "competitions.json")
    matches_root = DATA_ROOT / "matches"
    events_root  = DATA_ROOT / "events"

    # Bouw lijst van te verwerken (meta, event_path) paren
    all_matches = []
    for comp in competitions:
        cid  = comp["competition_id"]
        sid  = comp["season_id"]
        name = comp["competition_name"]

        # La Liga: alleen Messi-era; overige seizoenen overslaan
        if cid == LA_LIGA_CID and sid not in MESSI_ERA_SEASON_IDS:
            continue
        # Copa del Rey: geen Messi-era data
        if name == "Copa del Rey":
            continue

        mf = matches_root / str(cid) / f"{sid}.json"
        if not mf.exists():
            continue

        matches = load_json(mf)
        for m in matches:
            home = m["home_team"]["home_team_name"]
            away = m["away_team"]["away_team_name"]
            if BARCA_TEAM_NAME not in (home, away):
                continue

            ef = events_root / f"{m['match_id']}.json"
            if not ef.exists():
                continue

            comp_label = "La Liga" if cid == LA_LIGA_CID else name
            all_matches.append(({
                "match_id":    m["match_id"],
                "match_date":  m.get("match_date", ""),
                "competition": comp_label,
                "season":      comp.get("season_name", ""),
                "home_team":   home,
                "away_team":   away,
                "home_score":  m.get("home_score"),
                "away_score":  m.get("away_score"),
            }, ef))

    print(f"Verwerken: {len(all_matches)} Barcelona-matches\n")

    all_possessions = []
    totals = {k: 0 for k in ("total", "barca", "min_events", "messi", "shot", "progression")}

    for i, (meta, ef) in enumerate(all_matches, 1):
        if i % 50 == 0 or i == len(all_matches):
            print(f"  [{i:>3}/{len(all_matches)}] {meta['match_date']}  "
                  f"{meta['home_team']} vs {meta['away_team']}")
        poss, counts = process_match(meta, ef)
        all_possessions.extend(poss)
        for k in totals:
            totals[k] += counts[k]

    out_path = PROCESSED_DIR / "possessions_raw.json"
    with open(out_path, "wb") as f:
        f.write(json.dumps(all_possessions).encode())

    mb = out_path.stat().st_size / 1024 / 1024
    print(f"\n{'═' * 60}")
    print(f"  FILTER-VERSLAG ({len(all_matches)} matches)")
    print(f"{'═' * 60}")
    print(f"  Totaal possessions (alle teams):       {totals['total']:6d}")
    print(f"  Na filter 1 — Barcelona-bezit:         {totals['barca']:6d}")
    print(f"  Na filter 2 — ≥ {MIN_EVENTS} events:              {totals['min_events']:6d}")
    print(f"  Na filter 3 — Messi aanwezig:          {totals['messi']:6d}")
    print(f"  Na filter 4 — schot xG≥{MIN_XG}/doelpunt: {totals['shot']:6d}")
    print(f"  Na filter 5 — ≥{MIN_PROGRESSION:.0f}m progressie:       {totals['progression']:6d}")
    print(f"\n  Output: {out_path}  ({mb:.1f} MB)")
    print(f"{'═' * 60}")


if __name__ == "__main__":
    main()
