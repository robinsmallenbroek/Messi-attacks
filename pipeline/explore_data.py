"""
StatsBomb Open Data — exploratie voor Messi's FC Barcelona aanvallen.
Run vanuit pipeline/ met de venv actief:
  source venv/bin/activate && python explore_data.py
"""

import json
import os
from pathlib import Path

DATA_ROOT = Path(__file__).parent.parent / "data" / "statsbomb-open-data" / "data"

BARCA_TEAM_NAMES = {"Barcelona"}
MESSI_PLAYER = "Lionel Messi"


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def main():
    # ── 1. Competitions ────────────────────────────────────────
    section("1. Beschikbare competities met Barcelona-wedstrijden")

    competitions = load_json(DATA_ROOT / "competitions.json")

    # Filter: competition_name bevat 'La Liga' of andere comps met Barca
    la_liga = [c for c in competitions if c["competition_name"] == "La Liga"]
    other_barca = [
        c for c in competitions
        if c["competition_name"] != "La Liga"
        and c["competition_name"] not in ("La Liga",)
    ]

    print(f"\nLa Liga seizoenen in dataset ({len(la_liga)}):")
    for c in sorted(la_liga, key=lambda x: x["season_name"]):
        print(f"  {c['season_name']:20s}  competition_id={c['competition_id']}  season_id={c['season_id']}")

    # ── 2. Barcelona-matches per La Liga seizoen ───────────────
    section("2. FC Barcelona matches per La Liga seizoen")

    matches_root = DATA_ROOT / "matches"
    barca_matches_by_season: dict[str, list] = {}

    for comp in la_liga:
        cid = str(comp["competition_id"])
        sid = str(comp["season_id"])
        match_file = matches_root / cid / f"{sid}.json"
        if not match_file.exists():
            continue
        matches = load_json(match_file)
        barca = [
            m for m in matches
            if m["home_team"]["home_team_name"] in BARCA_TEAM_NAMES
            or m["away_team"]["away_team_name"] in BARCA_TEAM_NAMES
        ]
        if barca:
            barca_matches_by_season[comp["season_name"]] = barca

    total_matches = 0
    for season in sorted(barca_matches_by_season):
        n = len(barca_matches_by_season[season])
        total_matches += n
        print(f"  {season:20s}  {n:3d} wedstrijden")
    print(f"\n  Totaal: {total_matches} Barcelona La Liga wedstrijden")

    # ── 3. 360-data coverage ───────────────────────────────────
    section("3. 360-data coverage per seizoen")

    three_sixty_root = DATA_ROOT / "three-sixty"
    all_360_ids: set[str] = set()

    if three_sixty_root.exists():
        all_360_ids = {p.stem for p in three_sixty_root.glob("*.json")}
        print(f"\n  Totaal 360-bestanden beschikbaar: {len(all_360_ids)}")
    else:
        print("\n  three-sixty/ map nog niet gedownload of leeg.")

    for season in sorted(barca_matches_by_season):
        matches = barca_matches_by_season[season]
        with_360 = [m for m in matches if str(m["match_id"]) in all_360_ids]
        print(f"  {season:20s}  {len(with_360):3d}/{len(matches):3d} matches met 360-data")

    # ── 4. Event-structuur: sample van één match ───────────────
    section("4. Event-structuur — eerste 5 events van één Barcelona-match")

    # Pak de eerste beschikbare match uit het meest recente seizoen
    sample_match = None
    sample_season = None
    for season in sorted(barca_matches_by_season, reverse=True):
        if barca_matches_by_season[season]:
            sample_match = barca_matches_by_season[season][0]
            sample_season = season
            break

    if sample_match is None:
        print("  Geen matches gevonden.")
        return

    mid = sample_match["match_id"]
    home = sample_match["home_team"]["home_team_name"]
    away = sample_match["away_team"]["away_team_name"]
    date = sample_match.get("match_date", "?")
    print(f"\n  Match: {home} vs {away}  ({date}, {sample_season})  id={mid}")

    event_file = DATA_ROOT / "events" / f"{mid}.json"
    if not event_file.exists():
        print(f"  Event-bestand niet gevonden: {event_file}")
        return

    events = load_json(event_file)
    print(f"  Totaal events in deze match: {len(events)}\n")

    RELEVANT_KEYS = [
        "id", "index", "type", "timestamp", "minute", "second",
        "possession", "possession_team", "play_pattern",
        "team", "player", "position", "location",
        "duration", "under_pressure",
    ]

    for event in events[:5]:
        print(f"  ── Event {event.get('index', '?')} ──")
        for key in RELEVANT_KEYS:
            if key in event:
                val = event[key]
                # Simplify nested dicts to just the name field
                if isinstance(val, dict) and "name" in val:
                    val = val["name"]
                print(f"    {key:<20s}: {val}")
        # Toon ook eventuele type-specifieke subkeys
        etype = event.get("type", {}).get("name", "") if isinstance(event.get("type"), dict) else ""
        subkey = etype.lower().replace(" ", "_")
        if subkey in event:
            print(f"    [{subkey} details]     : {json.dumps(event[subkey], ensure_ascii=False)[:120]}")
        print()

    # ── 5. Velden-overzicht over alle event-types ──────────────
    section("5. Alle unieke event-types in deze match")
    event_types = sorted({
        (e.get("type") or {}).get("name", "unknown")
        for e in events
    })
    for t in event_types:
        count = sum(1 for e in events if (e.get("type") or {}).get("name") == t)
        print(f"  {t:<30s} {count:4d}×")

    print(f"\n{'═' * 60}")
    print("  Exploratie klaar.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
