#!/usr/bin/env python3
"""
Stap 2b (herzien): Score alle gefilterde possessions en genereer de longlist.
Laadt data/processed/possessions_raw.json → output/attacks_longlist.json.

Run: source venv/bin/activate && python score_attacks.py
"""

import ujson as json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import statistics

# ── Paden ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).parent
PROCESSED_DIR = SCRIPT_DIR.parent / "data" / "processed"
OUTPUT_DIR    = SCRIPT_DIR.parent / "output"
CONFIG_PATH   = SCRIPT_DIR / "config" / "iconic_attacks.json"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Score-gewichten (som = 1.0) ────────────────────────────────────────────────
W_OUTCOME     = 0.20
W_COMPLEXITY  = 0.20
W_PROGRESSION = 0.20
W_MESSI       = 0.20
W_RHYTHM      = 0.20

# outcome_score
XG_HIGH = 0.30
XG_MED  = 0.10

# complexity_score
EVENTS_OPT_MIN = 6
EVENTS_OPT     = 12
EVENTS_OPT_MAX = 25

# progression_score
ZONE_BOUNDARIES = [30.0, 60.0, 90.0]

# rhythm_score — sub-component parameters
PAUSE_THRESHOLD = 1.5   # seconden: interval ≥ dit telt als pauze
                        # NB: verlaagd van 2.0 naar 1.5 zodat ook subtiele pauzes
                        # (bijv. Betis-chip: langste gap = 1.944s) meedoen.
MAX_PAUSE_NORM  = 5.0   # seconden: pauze ≥ dit geeft pause_score = 1.0
W_PAUSE         = 0.25  # gewicht: magnitude van de pauze
W_CONTRAST      = 0.50  # gewicht: versnelling na de pauze (hoofdmeter)
W_ACCELERATION  = 0.25  # gewicht: algemeen toenemend tempo richting schot

MESSI_NAME = "Lionel Andrés Messi Cuccittini"


# ── Helpers ────────────────────────────────────────────────────────────────────

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


def ts_to_seconds(ts: str) -> float:
    try:
        h, m, rest = ts.split(":")
        return int(h) * 3600 + int(m) * 60 + float(rest)
    except Exception:
        return 0.0


def _pre_shot_events(events: list) -> list:
    """Geef events terug t/m (inclusief) het eerste Shot-event.
    Verwijdert post-schot ruis (Goal Keeper, Player Off, etc.) die anders
    kunstmatige lange intervals veroorzaken.
    """
    result = []
    for e in sorted(events, key=lambda x: x.get("index", 0)):
        result.append(e)
        if type_name(e) == "Shot":
            break
    return result


def _period_intervals(events: list) -> list:
    """Bereken inter-event tijden per periode (vermijdt rust-sprong).
    Geeft platte lijst van alle intervals ≥ 0.
    """
    by_period = defaultdict(list)
    for e in events:
        if "timestamp" in e:
            by_period[e.get("period", 1)].append(ts_to_seconds(e["timestamp"]))
    intervals = []
    for times in by_period.values():
        ts = sorted(times)
        for i in range(len(ts) - 1):
            iv = ts[i + 1] - ts[i]
            if iv >= 0:
                intervals.append(iv)
    return intervals


# ── Nieuwe rhythm-score ────────────────────────────────────────────────────────

def compute_rhythm_score(poss):
    """
    Bereken rhythm_score met 3 expliciete sub-componenten.

    Sub-componenten (elk 0-1):
      pause_score   — magnitude van de langste pauze (≥ PAUSE_THRESHOLD)
      contrast      — hoe veel sneller zijn de events ná de pauze
      acceleration  — neemt het tempo toe richting het schot

    Combinatie: pause_score * W_PAUSE + contrast * W_CONTRAST + acceleration * W_ACCELERATION
    Maximum bereik = 1.0; in de praktijk < 0.95 voor vrijwel alle aanvallen.
    """
    events    = _pre_shot_events(poss["events"])
    intervals = _period_intervals(events)

    if len(intervals) < 2:
        subs = {"pause_score": 0.0, "contrast": 0.0, "acceleration": 0.0}
        return 0.0, subs

    # ── Sub-component 1: pause_score ──────────────────────────────────────────
    # Vind de langste inter-event tijd ≥ PAUSE_THRESHOLD
    pauses = [(i, iv) for i, iv in enumerate(intervals) if iv >= PAUSE_THRESHOLD]

    if pauses:
        best_i, best_dur = max(pauses, key=lambda x: x[1])
        # Schaal: 0 bij exact PAUSE_THRESHOLD, 1.0 bij MAX_PAUSE_NORM+
        pause_score = min(1.0, (best_dur - PAUSE_THRESHOLD) / (MAX_PAUSE_NORM - PAUSE_THRESHOLD))
    else:
        best_i, best_dur = -1, 0.0
        pause_score = 0.0

    # ── Sub-component 2: contrast ─────────────────────────────────────────────
    # Hoe snel zijn de (maximaal 3) events direct ná de pauze?
    # Hoge contrast = korte post-pauze intervals t.o.v. de pauze-duur.
    if best_i >= 0:
        post_ivs = [iv for iv in intervals[best_i + 1: best_i + 4] if iv > 0.01]
        if post_ivs:
            med_post = statistics.median(post_ivs)
            contrast = max(0.0, min(1.0, 1.0 - med_post / (best_dur + 0.01)))
        else:
            contrast = 0.3   # pauze aanwezig maar geen zichtbaar vervolg
    else:
        contrast = 0.0

    # ── Sub-component 3: acceleration ────────────────────────────────────────
    # Vergelijk mediaan van de eerste 60% niet-nul intervals met de laatste 40%.
    # Positieve waarde = tempo neemt toe richting het schot.
    nz = [iv for iv in intervals if iv > 0.01]
    if len(nz) >= 4:
        split      = max(1, int(len(nz) * 0.6))
        med_early  = statistics.median(nz[:split])
        med_late   = statistics.median(nz[split:])
        if med_early > 0:
            acceleration = max(0.0, min(1.0, (med_early - med_late) / (med_early + 0.01)))
        else:
            acceleration = 0.0
    else:
        acceleration = 0.0

    score = round(min(1.0,
        pause_score  * W_PAUSE     +
        contrast     * W_CONTRAST  +
        acceleration * W_ACCELERATION
    ), 4)

    subs = {
        "pause_score":   round(pause_score,   4),
        "contrast":      round(contrast,      4),
        "acceleration":  round(acceleration,  4),
    }
    return score, subs


# ── Overige scoring-functies (ongewijzigd) ──────────────────────────────────────

def score_outcome(poss: dict) -> float:
    outcome = poss.get("shot_outcome") or ""
    xg      = poss.get("xg") or 0.0
    if outcome == "Goal":
        return 1.0
    if xg >= XG_HIGH:
        return 0.8
    if xg >= XG_MED:
        return 0.5
    return 0.2


def score_complexity(poss: dict) -> float:
    events = poss["events"]
    n = len(events)
    if n <= EVENTS_OPT_MIN:
        count_score = (n / EVENTS_OPT_MIN) * 0.5
    elif n <= EVENTS_OPT:
        count_score = 0.5 + (n - EVENTS_OPT_MIN) / (EVENTS_OPT - EVENTS_OPT_MIN) * 0.5
    elif n <= EVENTS_OPT_MAX:
        count_score = 1.0 - (n - EVENTS_OPT) / (EVENTS_OPT_MAX - EVENTS_OPT) * 0.2
    else:
        count_score = max(0.3, 0.8 - (n - EVENTS_OPT_MAX) / EVENTS_OPT_MAX * 0.3)
    types_present = {type_name(e) for e in events}
    variety_score = len(types_present & {"Pass", "Carry", "Dribble"}) / 3
    return round(count_score * 0.6 + variety_score * 0.4, 4)


def _zone_crossings(events: list) -> int:
    xs = [location_x(e) for e in events if location_x(e) is not None]
    if len(xs) < 2:
        return 0
    return sum(
        1 for i in range(1, len(xs))
        for b in ZONE_BOUNDARIES
        if xs[i - 1] < b <= xs[i]
    )


def score_progression(poss: dict) -> float:
    start_x    = poss.get("start_x") or 0.0
    end_x      = poss.get("end_x")   or 0.0
    prog_score = min(1.0, (max(0.0, end_x - start_x) - 30.0) / 60.0)
    zone_score = min(1.0, _zone_crossings(poss["events"]) / 3.0)
    return round(prog_score * 0.5 + zone_score * 0.5, 4)


def score_messi(poss: dict) -> float:
    events       = poss["events"]
    messi_events = [e for e in events if player_name(e) == MESSI_NAME]
    touch_score  = min(1.0, len(messi_events) / (max(1, len(events)) * 0.5))
    messi_types  = {type_name(e) for e in messi_events}
    messi_shot   = "Shot" in messi_types
    messi_goal   = messi_shot and poss.get("shot_outcome") == "Goal"
    bonus        = 0.4 if messi_goal else (0.2 if messi_shot else 0.0)
    return round(min(1.0, touch_score * 0.6 + bonus), 4)


def compute_total(scores: dict) -> float:
    return round(
        scores["outcome"]     * W_OUTCOME     +
        scores["complexity"]  * W_COMPLEXITY  +
        scores["progression"] * W_PROGRESSION +
        scores["messi"]       * W_MESSI       +
        scores["rhythm"]      * W_RHYTHM,
        4
    )


# ── Metadata-helpers ───────────────────────────────────────────────────────────

def event_breakdown(events: list) -> dict:
    RELEVANT = {"Pass", "Carry", "Dribble", "Shot", "Ball Receipt*",
                "Pressure", "Interception", "Ball Recovery", "Clearance", "Goalkeeper"}
    counts = Counter(type_name(e) for e in events)
    return {k: v for k, v in counts.items() if k in RELEVANT and v > 0}


def find_scorer(events: list):
    for e in events:
        if type_name(e) == "Shot":
            shot = e.get("shot") or {}
            if (shot.get("outcome") or {}).get("name") == "Goal":
                return player_name(e)
    return None


def find_assisting_player(events: list):
    shot_idx = next((e.get("index", 0) for e in events if type_name(e) == "Shot"), None)
    if shot_idx is None:
        return None
    passes_before = [e for e in events if type_name(e) == "Pass" and e.get("index", 0) < shot_idx]
    if not passes_before:
        return None
    return player_name(sorted(passes_before, key=lambda e: e.get("index", 0))[-1])


# ── Iconische match lookup via config ──────────────────────────────────────────

def _match_id_from_date(all_records, home, away, date_str, tolerance):
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None
    seen = set()
    for r in all_records:
        if r["home_team"] != home or r["away_team"] != away:
            continue
        mid = r["match_id"]
        if mid in seen:
            continue
        seen.add(mid)
        try:
            d = datetime.strptime(r["match_date"], "%Y-%m-%d")
            if abs((d - target).days) <= tolerance:
                return mid
        except ValueError:
            pass
    return None


def find_iconic_possession(scored, icon):
    """
    Zoek de iconische possession op via de config-definitie.

    Logica:
      1. Bepaal match_id via config.match_id of via datum+teams
      2. Filter possessions op target_minute ± tolerance
      3. Optioneel filter op target_outcome en target_player (als schutter)
      4. Kies de hoogst-scorende uit de resterende set
      5. Als leeg: return None (geen fallback)
    """
    # Stap 1: match_id
    if "match_id" in icon:
        mid = icon["match_id"]
    else:
        mid = _match_id_from_date(
            scored,
            icon.get("home_team", ""),
            icon.get("away_team", ""),
            icon.get("match_date", ""),
            icon.get("tolerance", 3),
        )

    if mid is None:
        return None

    candidates = [p for p in scored if p["match_id"] == mid]
    if not candidates:
        return None

    # Stap 2: minuut-filter
    tmin = icon.get("target_minute")
    tol  = icon.get("tolerance", 3)
    if tmin is not None:
        candidates = [p for p in candidates if abs(p["minute"] - tmin) <= tol]

    if not candidates:
        return None

    # Stap 3: uitkomst-filter
    tout = icon.get("target_outcome")
    if tout and tout != "Any":
        filtered = [p for p in candidates if p["outcome"] == tout]
        if filtered:
            candidates = filtered
        # als niets overblijft: geen verdere beperking (rapporteer wat we vinden)

    # Stap 4: speler-filter (schutter)
    tplyr = icon.get("target_player")
    if tplyr:
        filtered = [p for p in candidates if p.get("scorer") == tplyr]
        if filtered:
            candidates = filtered

    # Stap 5: hoogste score
    return max(candidates, key=lambda p: p["scores"]["total"])


# ── Validatie: rhythm-scores van de 5 testcases ───────────────────────────────

def rhythm_validation(raw: list):
    """Print rhythm sub-componenten voor de 5 validatie-aanvallen."""

    CASES = [
        {
            "label":    "Zaragoza-solo apr 2012 (rank 1 oud)",
            "match_id": 70219, "minute": 37,
            "verwacht": "nog steeds hoog",
        },
        {
            "label":    "Betis-chip mrt 2019 (verwacht: NU hoog)",
            "match_id": 16215, "minute": 45,
            "verwacht": "hoog — pauze + contrastversnelling",
        },
        {
            "label":    "El Clásico 5-0 nov 2010 (min 56)",
            "match_id": 69299, "minute": 56,
            "verwacht": "bekijken",
        },
        {
            "label":    "CL-finale 2011 — Messi-goal (poss=104, min=52)",
            "match_id": 18236, "possession_id": 104,
            "verwacht": "bekijken",
        },
        {
            "label":    "Ruis-aanval: min events, alles binnen 2s",
            "match_id": None,  # zoek de kortste possession
            "verwacht": "laag (geen pauze, geen contrast)",
        },
    ]

    print("\n" + "═" * 72)
    print("  RHYTHM-SCORE VALIDATIE — 5 TESTCASES")
    print("═" * 72)

    for case in CASES:
        if case["match_id"] is None:
            # Kortste possession zonder pauze
            poss = min(
                (r for r in raw if r["num_events"] <= 6),
                key=lambda r: r["duration_seconds"],
                default=None,
            )
        elif "possession_id" in case:
            poss = next(
                (r for r in raw
                 if r["match_id"] == case["match_id"]
                 and r["possession_id"] == case["possession_id"]),
                None,
            )
        else:
            poss = next(
                (r for r in raw
                 if r["match_id"] == case["match_id"]
                 and r["minute"] == case["minute"]),
                None,
            )

        print(f"\n  ── {case['label']}")
        print(f"     Verwacht: {case['verwacht']}")

        if poss is None:
            print("     → NIET GEVONDEN in possessions_raw.json")
            continue

        score, subs = compute_rhythm_score(poss)

        ivs      = _period_intervals(_pre_shot_events(poss["events"]))
        pauses   = [iv for iv in ivs if iv >= PAUSE_THRESHOLD]
        max_iv   = max(ivs) if ivs else 0

        print(f"     match={poss['match_id']} | poss={poss['possession_id']} | "
              f"min={poss['minute']} | outcome={poss['shot_outcome']}")
        print(f"     Langste gap: {max_iv:.3f}s | Pauzes ≥{PAUSE_THRESHOLD}s: "
              f"{[round(p,2) for p in pauses]}")
        print(f"     pause_score={subs['pause_score']:.3f}  "
              f"contrast={subs['contrast']:.3f}  "
              f"acceleration={subs['acceleration']:.3f}")
        print(f"     → rhythm_score = {score:.4f}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    raw_path = PROCESSED_DIR / "possessions_raw.json"
    if not raw_path.exists():
        print("FOUT: possessions_raw.json niet gevonden. Draai eerst extract_possessions.py")
        return

    print(f"Laden: {raw_path} ...", end=" ", flush=True)
    raw = load_json(raw_path)
    print(f"{len(raw)} possessions")

    # ── Score alle possessions ─────────────────────────────────────────────────
    scored = []
    for poss in raw:
        events = poss["events"]
        rhythm, rhythm_subs = compute_rhythm_score(poss)
        scores = {
            "outcome":      score_outcome(poss),
            "complexity":   score_complexity(poss),
            "progression":  score_progression(poss),
            "messi":        score_messi(poss),
            "rhythm":       rhythm,
            "rhythm_subs":  rhythm_subs,   # bewaar voor inspectie
        }
        scores["total"] = compute_total(scores)

        outcome_raw   = poss.get("shot_outcome") or ""
        VALID_OUTCOMES = {"Goal", "Saved", "Blocked", "Off T", "Wayward", "Post"}
        outcome_label = outcome_raw if outcome_raw in VALID_OUTCOMES else "Other"

        record = {
            "match_id":             poss["match_id"],
            "match_date":           poss["match_date"],
            "competition":          poss["competition"],
            "season":               poss["season"],
            "home_team":            poss["home_team"],
            "away_team":            poss["away_team"],
            "score":                f"{poss['home_score']}-{poss['away_score']}",
            "possession_id":        poss["possession_id"],
            "minute":               poss["minute"],
            "duration_seconds":     poss["duration_seconds"],
            "num_events":           poss["num_events"],
            "event_type_breakdown": event_breakdown(events),
            "messi_touches":        sum(1 for e in events if player_name(e) == MESSI_NAME),
            "outcome":              outcome_label,
            "xg":                   poss.get("xg"),
            "shot_location":        poss.get("shot_location"),
            "scorer":               find_scorer(events),
            "assisting_player":     find_assisting_player(events),
            "has_freeze_frame":     poss.get("has_freeze_frame", False),
            "scores":               scores,
            "is_iconic":            False,
            "iconic_label":         None,
        }
        scored.append(record)

    scored.sort(key=lambda p: p["scores"]["total"], reverse=True)

    # ── Rhythm-validatie ───────────────────────────────────────────────────────
    rhythm_validation(raw)

    # ── Iconische matches via config ───────────────────────────────────────────
    icons = load_json(CONFIG_PATH)

    print("\n" + "═" * 72)
    print("  ICONISCHE MATCHES — VERIFICATIE (config-gebaseerd)")
    print("═" * 72)

    for icon in icons:
        label = icon["label"]
        best  = find_iconic_possession(scored, icon)

        if best is None:
            print(f"\n  ✗ NIET GEVONDEN: {label}")
            note = icon.get("_note", "")
            if note:
                print(f"    Noot: {note}")
            continue

        best["is_iconic"]    = True
        best["iconic_label"] = label
        s = best["scores"]
        rank = next((i + 1 for i, r in enumerate(scored) if r is best), "?")
        print(f"\n  ✓ {label}")
        print(f"    match_id={best['match_id']} | poss={best['possession_id']} | "
              f"min={best['minute']} | rank #{rank}")
        print(f"    Uitkomst={best['outcome']} | xG={best['xg']} | "
              f"Scorer={best['scorer']} | Score={s['total']:.3f}")
        print(f"    O={s['outcome']:.2f} C={s['complexity']:.2f} "
              f"P={s['progression']:.2f} M={s['messi']:.2f} R={s['rhythm']:.2f}")
        note = icon.get("_note", "")
        if note:
            print(f"    ⚑  {note}")

    # ── Schrijf output ─────────────────────────────────────────────────────────
    out_path = OUTPUT_DIR / "attacks_longlist.json"
    with open(out_path, "wb") as f:
        f.write(json.dumps(scored, indent=2).encode())

    # ── Terminal verslag ───────────────────────────────────────────────────────
    all_totals    = sorted(p["scores"]["total"] for p in scored)
    all_rhythms   = sorted(p["scores"]["rhythm"] for p in scored)
    n             = len(all_totals)
    old_top20_ids = {
        (70219, 71), (69328, None), (267564, None), (69299, 112), (16215, 95),
    }  # rough reference voor vergelijking

    def pct(lst, p):
        return lst[min(int(len(lst) * p / 100), len(lst) - 1)]

    rhythm_above_09 = sum(1 for r in all_rhythms if r >= 0.9)

    print("\n" + "═" * 96)
    print("  TOP 20 AANVALLEN OP TOTAALSCORE")
    print("═" * 96)
    hdr = (f"  {'#':>3}  {'Datum':10}  {'Match':32}  {'Min':>4}  "
           f"{'Uitkomst':8}  {'xG':>5}  {'Tot':>5}  O/C/P/M/R")
    print(hdr)
    print("  " + "─" * 92)

    for i, r in enumerate(scored[:20], 1):
        s   = r["scores"]
        m   = f"{r['home_team']} vs {r['away_team']}"[:31]
        xg  = f"{r['xg']:.3f}" if r["xg"] else "  —  "
        bd  = (f"{s['outcome']:.2f}/{s['complexity']:.2f}/"
               f"{s['progression']:.2f}/{s['messi']:.2f}/{s['rhythm']:.2f}")
        flg = " ★" if r["is_iconic"] else ""
        print(f"  {i:>3}  {r['match_date']}  {m:32}  {r['minute']:>4}  "
              f"{r['outcome']:8}  {xg:>5}  {s['total']:.3f}{flg}  {bd}")

    print()
    print("═" * 72)
    print("  RHYTHM-SCORE DISTRIBUTIE")
    print("═" * 72)
    for p in (0, 10, 25, 50, 75, 90, 95, 99, 100):
        print(f"  P{p:>3}: {pct(all_rhythms, p):.3f}")
    print(f"\n  Aanvallen met rhythm ≥ 0.9:  {rhythm_above_09} ({100*rhythm_above_09/n:.1f}%)")
    print(f"  Aanvallen met rhythm = 1.00: {sum(1 for r in all_rhythms if r >= 1.0)}")

    print()
    print("═" * 72)
    print("  TOTAALSCORE DISTRIBUTIE")
    print("═" * 72)
    for p in (0, 10, 25, 50, 75, 90, 95, 99, 100):
        print(f"  P{p:>3}: {pct(all_totals, p):.3f}")

    print()
    print("═" * 72)
    print("  SAMENVATTING")
    print("═" * 72)
    print(f"  Possessions gescoord:        {n}")
    print(f"  Doelpunten:                  {sum(1 for p in scored if p['outcome']=='Goal')}")
    print(f"  Iconisch gemarkeerd:         {sum(1 for p in scored if p['is_iconic'])}")
    print(f"  Output: {out_path}  ({out_path.stat().st_size/1024:.0f} KB)")
    print("═" * 72)


if __name__ == "__main__":
    main()
