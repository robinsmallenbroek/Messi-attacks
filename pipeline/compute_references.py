#!/usr/bin/env python3
"""
Compute dataset-wide reference statistics across all 2,339 qualifying attacks.

Output: output/reference_stats.json
Used by the frontend to contextualize per-attack signals:
"In this attack: 1.2m to nearest defender — krapper dan 96% van Barcelona-schoten."

Two groups of metrics:
  - "hoe":     pass precision, pressure rate, dribble success, opponents beaten,
               direction changes, space at shot, pass-chain length, unique teammates
  - "wanneer": ball speed during carries/passes, acceleration, pauses,
               progression speed, total duration

Where it makes sense, each metric has two variants:
  - "all":     across all Barcelona events in qualifying possessions
  - "messi":   filtered to Messi's events only

Run:  source venv/bin/activate && python compute_references.py
"""

import math
import statistics
import ujson as json
from collections import defaultdict
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).parent
PROCESSED_DIR = SCRIPT_DIR.parent / "data" / "processed"
OUTPUT_DIR    = SCRIPT_DIR.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

MESSI_NAME = "Lionel Andrés Messi Cuccittini"
BARCA_NAME = "Barcelona"
VERSION    = "2026-05-23"

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_json(path):
    with open(path, "rb") as f:
        return json.load(f)


def type_name(e):
    t = e.get("type")
    return t["name"] if isinstance(t, dict) else ""


def player_name(e):
    p = e.get("player")
    return p["name"] if isinstance(p, dict) else None


def team_name(e):
    t = e.get("team")
    return t["name"] if isinstance(t, dict) else None


def ts_seconds(ts):
    try:
        h, m, rest = ts.split(":")
        return int(h) * 3600 + int(m) * 60 + float(rest)
    except Exception:
        return 0.0


def percentiles(values, pcts=(10, 25, 50, 75, 90, 95, 99)):
    """Return dict with percentiles + mean + n.  None-valued samples filtered out."""
    cleaned = [v for v in values if v is not None]
    if not cleaned:
        return {"n": 0, "mean": None, "median": None,
                **{f"p{p}": None for p in pcts}, "min": None, "max": None}
    sv = sorted(cleaned)
    n = len(sv)
    out = {"n": n,
           "mean":   round(statistics.mean(sv), 4),
           "median": round(statistics.median(sv), 4),
           "min":    round(sv[0], 4),
           "max":    round(sv[-1], 4)}
    for p in pcts:
        idx = min(int(n * p / 100), n - 1)
        out[f"p{p}"] = round(sv[idx], 4)
    return out


# ── Per-possession computation ─────────────────────────────────────────────────

def pass_success_rate(passes):
    if not passes:
        return None
    succ = sum(1 for e in passes if not (e.get("pass") or {}).get("outcome"))
    return succ / len(passes)


def pressure_fraction(evs):
    if not evs:
        return None
    return sum(1 for e in evs if e.get("under_pressure", False)) / len(evs)


def dribble_complete_rate(dribbles):
    if not dribbles:
        return None
    succ = sum(1 for e in dribbles
               if (e.get("dribble") or {}).get("outcome", {}).get("name") == "Complete")
    return succ / len(dribbles)


def count_direction_changes(events, player_filter=None):
    """For each carry, compare its direction vector to the vector toward the
    next event location.  Count where the angle exceeds 45 degrees."""
    sorted_evs = sorted(events, key=lambda e: e.get("index", 0))
    changes = 0
    for i, e in enumerate(sorted_evs):
        if type_name(e) != "Carry":
            continue
        if player_filter and player_name(e) != player_filter:
            continue
        loc = e.get("location")
        end = (e.get("carry") or {}).get("end_location")
        if not loc or not end:
            continue
        # Direction of carry
        v1 = (end[0] - loc[0], end[1] - loc[1])
        if v1[0] * v1[0] + v1[1] * v1[1] < 0.04:
            continue
        # Vector from carry-end to next event with location
        next_loc = None
        for j in range(i + 1, len(sorted_evs)):
            nl = sorted_evs[j].get("location")
            if nl:
                next_loc = nl
                break
        if not next_loc:
            continue
        v2 = (next_loc[0] - end[0], next_loc[1] - end[1])
        if v2[0] * v2[0] + v2[1] * v2[1] < 0.04:
            continue
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        mag = math.sqrt((v1[0] ** 2 + v1[1] ** 2) * (v2[0] ** 2 + v2[1] ** 2))
        if mag == 0:
            continue
        cos = max(-1.0, min(1.0, dot / mag))
        angle_deg = math.degrees(math.acos(cos))
        if angle_deg > 45:
            changes += 1
    return changes


def space_at_shot(events, freeze_frame):
    """Distance from the shooter to the nearest non-keeper opponent.
    Returns (overall_distance, is_messi_shooter)."""
    shot = next((e for e in events if type_name(e) == "Shot"), None)
    if not shot or not shot.get("location"):
        return None, False
    shot_loc = shot["location"]
    distances = []
    for p in freeze_frame or []:
        if p.get("teammate", False):
            continue
        if (p.get("position") or {}).get("name") == "Goalkeeper":
            continue
        ploc = p.get("location")
        if not ploc:
            continue
        distances.append(math.hypot(ploc[0] - shot_loc[0], ploc[1] - shot_loc[1]))
    if not distances:
        return None, False
    is_messi = player_name(shot) == MESSI_NAME
    return min(distances), is_messi


def carry_speeds(carries):
    out = []
    for c in carries:
        loc = c.get("location")
        end = (c.get("carry") or {}).get("end_location")
        dur = c.get("duration")
        if loc and end and dur and dur > 0.1:
            d = math.hypot(end[0] - loc[0], end[1] - loc[1])
            out.append(d / dur)
    return out


def pass_speeds(passes):
    """Use StatsBomb's pass.length (in pitch meters) divided by event duration."""
    out = []
    for p in passes:
        length = (p.get("pass") or {}).get("length")
        dur = p.get("duration")
        if length and dur and dur > 0.1:
            out.append(length / dur)
    return out


def accelerations(events, player_filter=None):
    """Compute |Δspeed| between consecutive ball-events.  Crude estimate, but
    captures bursts in tempo over the course of a possession."""
    BALL_TYPES = {"Pass", "Ball Receipt*", "Carry", "Dribble", "Shot",
                  "Interception", "Ball Recovery", "Clearance", "Goal Keeper"}
    seq = []
    for e in events:
        if type_name(e) not in BALL_TYPES:
            continue
        if not e.get("location") or "timestamp" not in e:
            continue
        if player_filter and player_name(e) != player_filter:
            continue
        seq.append((ts_seconds(e["timestamp"]), e["location"]))
    seq.sort(key=lambda x: x[0])
    speeds = []
    for i in range(1, len(seq)):
        dt = seq[i][0] - seq[i - 1][0]
        if dt > 0.1:
            dx = seq[i][1][0] - seq[i - 1][1][0]
            dy = seq[i][1][1] - seq[i - 1][1][1]
            speeds.append((seq[i][0], math.hypot(dx, dy) / dt))
    out = []
    for i in range(1, len(speeds)):
        dt = speeds[i][0] - speeds[i - 1][0]
        if dt > 0.1:
            out.append(abs(speeds[i][1] - speeds[i - 1][1]) / dt)
    return out


def pauses(events):
    """Inter-event gaps (seconds), computed within each period."""
    by_period = defaultdict(list)
    for e in events:
        if "timestamp" in e:
            by_period[e.get("period", 1)].append(ts_seconds(e["timestamp"]))
    gaps = []
    for times in by_period.values():
        ts_sorted = sorted(times)
        for i in range(1, len(ts_sorted)):
            gaps.append(ts_sorted[i] - ts_sorted[i - 1])
    return gaps


def progression_speed(events, duration):
    """Forward progression speed: (last_x - first_x) / duration, using
    Barcelona-team events only (their x is in Barca's attacking frame)."""
    locs = [e["location"] for e in events
            if e.get("location") and team_name(e) == BARCA_NAME]
    if len(locs) < 2 or duration <= 0:
        return None
    return (locs[-1][0] - locs[0][0]) / duration


# ── Trim helper ────────────────────────────────────────────────────────────────

def trim_to_shot(events):
    """Keep only events up to and including the first Shot.  Possessions_raw.json
    keeps the full possession group, which often contains admin events after the
    shot (Goal Keeper, Substitution, Player Off, Half End) with huge timestamp
    gaps.  Those pollute durations, max-pauses, and unique-teammate counts."""
    sorted_evs = sorted(events, key=lambda x: x.get("index", 0))
    out = []
    for e in sorted_evs:
        out.append(e)
        if type_name(e) == "Shot":
            break
    return out


def attack_duration(events):
    """Duration in seconds from first to last event of the trimmed attack."""
    if len(events) < 2:
        return 0.0
    ts = [ts_seconds(e["timestamp"]) for e in events if "timestamp" in e]
    if not ts:
        return 0.0
    # Use min/max within each period to handle the half-time edge case
    by_period = defaultdict(list)
    for e in events:
        if "timestamp" in e:
            by_period[e.get("period", 1)].append(ts_seconds(e["timestamp"]))
    total = 0.0
    for tt in by_period.values():
        total += max(tt) - min(tt)
    return total


# ── Main per-possession aggregator ─────────────────────────────────────────────

def per_possession(poss):
    events = trim_to_shot(poss["events"])
    barca_events = [e for e in events if team_name(e) == BARCA_NAME]
    messi_events = [e for e in events if player_name(e) == MESSI_NAME]

    passes_all   = [e for e in barca_events if type_name(e) == "Pass"]
    passes_messi = [e for e in messi_events if type_name(e) == "Pass"]
    dribbles_all = [e for e in barca_events if type_name(e) == "Dribble"]
    dribbles_messi = [e for e in messi_events if type_name(e) == "Dribble"]
    carries_all  = [e for e in barca_events if type_name(e) == "Carry"]
    carries_messi = [e for e in messi_events if type_name(e) == "Carry"]

    space, messi_shooter = space_at_shot(events, poss.get("freeze_frame"))

    return {
        # Hoe — per-possession scalars (one value per possession)
        "pass_precision_all":    pass_success_rate(passes_all),
        "pass_precision_messi":  pass_success_rate(passes_messi),
        "pressure_rate_all":     pressure_fraction(barca_events),
        "pressure_rate_messi":   pressure_fraction(messi_events),
        "dribble_success_all":   dribble_complete_rate(dribbles_all),
        "dribble_success_messi": dribble_complete_rate(dribbles_messi),
        "opp_beaten_all":        sum(1 for d in dribbles_all if (d.get("dribble") or {}).get("outcome", {}).get("name") == "Complete"),
        "opp_beaten_messi":      sum(1 for d in dribbles_messi if (d.get("dribble") or {}).get("outcome", {}).get("name") == "Complete"),
        "dir_changes_all":       count_direction_changes(events),
        "dir_changes_messi":     count_direction_changes(events, player_filter=MESSI_NAME),
        "space_to_nearest_all":  space,
        "space_to_nearest_messi": space if messi_shooter else None,
        "pass_chain_len":        len(passes_all),
        "unique_teammates":      len({player_name(e) for e in barca_events if player_name(e)}),
        # Wanneer — per-possession scalars (using trimmed events)
        "n_pauses_2s":           sum(1 for g in pauses(events) if g >= 2.0),
        "max_pause":             max(pauses(events)) if pauses(events) else 0,
        "progression_speed":     progression_speed(events, attack_duration(events)),
        "total_duration":        attack_duration(events),
        # Wanneer — per-event lists (flattened across dataset for true distributions)
        "_carry_speeds_all":     carry_speeds(carries_all),
        "_carry_speeds_messi":   carry_speeds(carries_messi),
        "_pass_speeds_all":      pass_speeds(passes_all),
        "_pass_speeds_messi":    pass_speeds(passes_messi),
        "_accels_all":           accelerations(barca_events),
        "_accels_messi":         accelerations(messi_events, player_filter=MESSI_NAME),
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    raw_path = PROCESSED_DIR / "possessions_raw.json"
    if not raw_path.exists():
        print("FOUT: possessions_raw.json niet gevonden — draai eerst extract_possessions.py")
        return

    print(f"Loading {raw_path} ...", end=" ", flush=True)
    raw = load_json(raw_path)
    print(f"{len(raw)} possessions")

    per_poss = []
    for p in raw:
        per_poss.append(per_possession(p))

    def collect(key):
        return [m.get(key) for m in per_poss]

    def collect_flat(key):
        out = []
        for m in per_poss:
            v = m.get(key, [])
            if isinstance(v, list):
                out.extend(v)
        return out

    output = {
        "version":       VERSION,
        "n_possessions": len(raw),
        "note":          ("Per-possession scalar stats (mean/percentiles across all qualifying attacks). "
                          "Speed/acceleration metrics with leading underscore in source are flattened "
                          "across every individual event in the dataset, not per-possession aggregates."),
        "hoe": {
            "pass_precision":         {"all": percentiles(collect("pass_precision_all")),
                                       "messi": percentiles(collect("pass_precision_messi"))},
            "pressure_rate":          {"all": percentiles(collect("pressure_rate_all")),
                                       "messi": percentiles(collect("pressure_rate_messi"))},
            "dribble_success":        {"all": percentiles(collect("dribble_success_all")),
                                       "messi": percentiles(collect("dribble_success_messi"))},
            "opponents_beaten":       {"all": percentiles(collect("opp_beaten_all")),
                                       "messi": percentiles(collect("opp_beaten_messi"))},
            "direction_changes":      {"all": percentiles(collect("dir_changes_all")),
                                       "messi": percentiles(collect("dir_changes_messi"))},
            "space_to_nearest_at_shot_m": {"all": percentiles(collect("space_to_nearest_all")),
                                           "messi": percentiles(collect("space_to_nearest_messi"))},
            "pass_chain_length":      percentiles(collect("pass_chain_len")),
            "unique_teammates":       percentiles(collect("unique_teammates")),
        },
        "wanneer": {
            "carry_speed_mps":        {"all": percentiles(collect_flat("_carry_speeds_all")),
                                       "messi": percentiles(collect_flat("_carry_speeds_messi"))},
            "pass_speed_mps":         {"all": percentiles(collect_flat("_pass_speeds_all")),
                                       "messi": percentiles(collect_flat("_pass_speeds_messi"))},
            "acceleration_mps2":      {"all": percentiles(collect_flat("_accels_all")),
                                       "messi": percentiles(collect_flat("_accels_messi"))},
            "n_pauses_2s":            percentiles(collect("n_pauses_2s")),
            "max_pause_s":            percentiles(collect("max_pause")),
            "progression_speed_mps":  percentiles(collect("progression_speed")),
            "total_duration_s":       percentiles(collect("total_duration")),
        },
    }

    out_path = OUTPUT_DIR / "reference_stats.json"
    with open(out_path, "wb") as f:
        f.write(json.dumps(output, indent=2).encode())
    print(f"\nWrote {out_path}  ({out_path.stat().st_size / 1024:.1f} KB)")

    print_summary(output)


# ── Markdown summary + plausibility checks ─────────────────────────────────────

def fmt(v, suffix=""):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}{suffix}"
    return f"{v}{suffix}"


def row(label, s, suffix=""):
    return (f"| {label} | {fmt(s.get('mean'), suffix)} | {fmt(s.get('median'), suffix)} "
            f"| {fmt(s.get('p75'), suffix)} | {fmt(s.get('p95'), suffix)} "
            f"| {fmt(s.get('p99'), suffix)} | {s.get('n', 0)} |")


def print_summary(out):
    print("\n" + "═" * 78)
    print(f"  REFERENTIE-STATISTIEKEN  ({out['n_possessions']} possessions, v{out['version']})")
    print("═" * 78)

    header = "| Metric | gem. | mediaan | p75 | p95 | p99 | n |"
    sep    = "|---|---|---|---|---|---|---|"

    print("\n### Hoe-lens")
    print(header)
    print(sep)
    h = out["hoe"]
    print(row("Pass-precisie (all, % per poss)",      h["pass_precision"]["all"], ""))
    print(row("Pass-precisie (Messi)",                h["pass_precision"]["messi"], ""))
    print(row("Onder-druk frequentie (all)",          h["pressure_rate"]["all"], ""))
    print(row("Onder-druk frequentie (Messi)",        h["pressure_rate"]["messi"], ""))
    print(row("Dribble succes-rate (all)",            h["dribble_success"]["all"], ""))
    print(row("Dribble succes-rate (Messi)",          h["dribble_success"]["messi"], ""))
    print(row("Tegenstanders gepasseerd (all)",       h["opponents_beaten"]["all"]))
    print(row("Tegenstanders gepasseerd (Messi)",     h["opponents_beaten"]["messi"]))
    print(row("Richtingswisselingen (all)",           h["direction_changes"]["all"]))
    print(row("Richtingswisselingen (Messi-carries)", h["direction_changes"]["messi"]))
    print(row("Ruimte tot tegenstander schot (all m)",h["space_to_nearest_at_shot_m"]["all"], " m"))
    print(row("Ruimte tot tegenstander schot (Messi)",h["space_to_nearest_at_shot_m"]["messi"], " m"))
    print(row("Pass-keten lengte",                    h["pass_chain_length"]))
    print(row("Unieke teamgenoten",                   h["unique_teammates"]))

    print("\n### Wanneer-lens")
    print(header)
    print(sep)
    w = out["wanneer"]
    print(row("Bal-snelheid carries (all m/s)",       w["carry_speed_mps"]["all"], " m/s"))
    print(row("Bal-snelheid carries (Messi)",         w["carry_speed_mps"]["messi"], " m/s"))
    print(row("Bal-snelheid passes (all m/s)",        w["pass_speed_mps"]["all"], " m/s"))
    print(row("Bal-snelheid passes (Messi)",          w["pass_speed_mps"]["messi"], " m/s"))
    print(row("Acceleratie (all m/s²)",               w["acceleration_mps2"]["all"], " m/s²"))
    print(row("Acceleratie (Messi)",                  w["acceleration_mps2"]["messi"], " m/s²"))
    print(row("Aantal pauzes ≥ 2s",                   w["n_pauses_2s"]))
    print(row("Max pauze-lengte (s)",                 w["max_pause_s"], " s"))
    print(row("Progressie-snelheid (m/s)",            w["progression_speed_mps"], " m/s"))
    print(row("Totale duur (s)",                      w["total_duration_s"], " s"))

    # ── Plausibility checks ────────────────────────────────────────────────────
    print("\n### Plausibility checks\n")
    cs_all = w["carry_speed_mps"]["all"]
    cs_messi = w["carry_speed_mps"]["messi"]

    def check(label, ok, msg):
        marker = "✓" if ok else "⚠"
        print(f"  {marker}  {label}: {msg}")

    check("Bal-snelheid carries gemiddelde (verwacht 2–8 m/s)",
          cs_all["mean"] is not None and 2 <= cs_all["mean"] <= 8,
          f"{cs_all['mean']} m/s")

    a_all = w["acceleration_mps2"]["all"]
    a_messi = w["acceleration_mps2"]["messi"]
    if a_all["p99"] is not None and a_messi["p99"] is not None:
        check("Top 1% Messi-acties heeft hogere acceleratie dan top 1% alle acties",
              a_messi["p99"] > a_all["p99"],
              f"Messi p99={a_messi['p99']} vs alle p99={a_all['p99']} m/s²")

    pp_all = h["pass_precision"]["all"]
    check("Pass-precisie all gemiddelde (verwacht 0.75–0.95)",
          pp_all["mean"] is not None and 0.75 <= pp_all["mean"] <= 0.95,
          f"{pp_all['mean']:.3f}")

    space_all = h["space_to_nearest_at_shot_m"]["all"]
    check("Ruimte bij schot mediaan (verwacht 1–4 m)",
          space_all["median"] is not None and 1 <= space_all["median"] <= 4,
          f"{space_all['median']} m")

    dur = w["total_duration_s"]
    check("Possession-duur p99 onder 60 s",
          dur["p99"] is not None and dur["p99"] < 60,
          f"p99={dur['p99']} s")

    print("\n" + "═" * 78)


if __name__ == "__main__":
    main()
