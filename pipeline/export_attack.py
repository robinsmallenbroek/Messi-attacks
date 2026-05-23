#!/usr/bin/env python3
"""
Stap 3: Exporteer één possession naar een schone JSON voor de frontend.
Default: Zaragoza-solo 2012-04-07, match_id=70219, possession_id=71.

Output: frontend/src/data/zaragoza_2012.json

Run: source venv/bin/activate && python export_attack.py
"""

import ujson as json
import math
from pathlib import Path

# ── Paden ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
DATA_ROOT   = SCRIPT_DIR.parent / "data" / "statsbomb-open-data" / "data"
RAW_PATH    = SCRIPT_DIR.parent / "data" / "processed" / "possessions_raw.json"
OUTPUT_PATH = SCRIPT_DIR.parent / "frontend" / "src" / "data" / "zaragoza_2012.json"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Configuratie ──────────────────────────────────────────────────────────────
MATCH_ID      = 70219
POSSESSION_ID = 71
MESSI_NAME    = "Lionel Andrés Messi Cuccittini"
BARCA_NAME    = "Barcelona"

# Velden in 120×80 StatsBomb-coördinaten
PITCH_LENGTH = 120.0
PITCH_WIDTH  = 80.0


def to_barca_frame(loc, team):
    """StatsBomb registreert event-locaties vanuit het perspectief van het
    UITVOERENDE team (aanvallende doel = x=120). Voor opponent-events (zoals
    Pressure door Zaragoza op Barca-spelers) moeten we spiegelen naar Barca's
    aanvalsrichting, anders staan tegenstanders op de verkeerde plek."""
    if not loc:
        return None
    if team != BARCA_NAME:
        return [PITCH_LENGTH - loc[0], PITCH_WIDTH - loc[1]]
    return list(loc)


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


def player_id(e):
    p = e.get("player")
    return p.get("id") if isinstance(p, dict) else None


def team_name(e):
    t = e.get("team")
    return t["name"] if isinstance(t, dict) else None


def ts_seconds(ts):
    try:
        h, m, rest = ts.split(":")
        return int(h) * 3600 + int(m) * 60 + float(rest)
    except Exception:
        return 0.0


def short_name(full):
    """Kort weergaveformaat: laatste woord, met uitzonderingen voor bekende spelers."""
    if not full:
        return ""
    SHORT = {
        "Lionel Andrés Messi Cuccittini": "Messi",
        "Xavier Hernández Creus":         "Xavi",
        "Andrés Iniesta Luján":           "Iniesta",
        "Daniel Alves da Silva":          "Dani Alves",
        "Sergio Busquets i Burgos":       "Busquets",
        "Pedro Eliezer Rodríguez Ledesma":"Pedro",
        "David Villa Sánchez":            "Villa",
        "Alexis Alejandro Sánchez Sánchez":"Alexis",
        "Francesc Fàbregas i Soler":      "Cesc",
        "Thiago Alcântara do Nascimento": "Thiago",
        "Cristian Gabriel Tello Herrera": "Tello",
    }
    if full in SHORT:
        return SHORT[full]
    parts = full.split()
    return parts[-1] if parts else full


# ── Hoofdlogica ────────────────────────────────────────────────────────────────

def main():
    # ── Match-metadata ─────────────────────────────────────────────────────────
    # Zoek de match via possessions_raw.json (heeft al alle metadata)
    raw_poss_list = load_json(RAW_PATH)
    poss_record = next(
        (r for r in raw_poss_list
         if r["match_id"] == MATCH_ID and r["possession_id"] == POSSESSION_ID),
        None,
    )
    if poss_record is None:
        print(f"FOUT: possession {POSSESSION_ID} in match {MATCH_ID} niet gevonden")
        return

    # ── Volledige raw events van de match (voor related_events lookup) ─────────
    all_events = load_json(DATA_ROOT / "events" / f"{MATCH_ID}.json")
    events_by_id = {e["id"]: e for e in all_events}

    # Possession-events: filter raw events op possession_id (krijgt volledige data,
    # niet de trimmed versie uit possessions_raw.json)
    poss_events = [e for e in all_events if e.get("possession") == POSSESSION_ID
                   and (e.get("possession_team") or {}).get("name") == BARCA_NAME]
    poss_events.sort(key=lambda e: e.get("index", 0))

    # Knip af na de Shot om post-shot ruis (Goal Keeper, Player Off) te verwijderen
    shot_index = None
    for e in poss_events:
        if type_name(e) == "Shot":
            shot_index = e.get("index")
            break
    if shot_index is not None:
        poss_events = [e for e in poss_events if e.get("index", 0) <= shot_index]

    print(f"Match {MATCH_ID} | Possession {POSSESSION_ID} | {len(poss_events)} events na trim")

    # ── Validatie-print (zoals gevraagd) ────────────────────────────────────────
    print("\n── Validatie: eerste 2 + laatste 2 events ──")
    for label, evs in [("eerste 2", poss_events[:2]), ("laatste 2", poss_events[-2:])]:
        print(f"  {label}:")
        for e in evs:
            print(f"    idx={e['index']:>3} t={e['timestamp']} "
                  f"min={e.get('minute', '?')}  type={type_name(e):<14s} "
                  f"player={short_name(player_name(e))}")
    shot_ev = next((e for e in poss_events if type_name(e) == "Shot"), None)
    outcome = (shot_ev.get("shot") or {}).get("outcome", {}).get("name") if shot_ev else None
    print(f"  Minuut start: {poss_events[0].get('minute')}  |  Shot-outcome: {outcome}")

    # ── Berekende velden per event ─────────────────────────────────────────────
    cum_messi_touches = 0
    opponents_beaten  = 0

    # Voor inter_event_seconds: vorige timestamp (alle events tellen mee)
    prev_t = None
    # Voor ball_speed_mps: alleen bal-events tellen (Pressure-events tonen
    # de tegenstander's positie, niet de bal — die zouden de speed onzin maken)
    BALL_EVENTS = {"Pass", "Ball Receipt*", "Carry", "Dribble", "Shot",
                   "Interception", "Ball Recovery", "Clearance", "Miscontrol",
                   "Goal Keeper", "Block"}
    prev_ball_t   = None
    prev_ball_loc = None

    exported_events = []

    for e in poss_events:
        t_now  = ts_seconds(e["timestamp"])
        team   = team_name(e)
        loc    = to_barca_frame(e.get("location"), team)
        typ    = type_name(e)
        plyr   = player_name(e)

        # Inter-event seconden (alle events tellen; eerste event = 0)
        inter = 0.0 if prev_t is None else max(0.0, t_now - prev_t)

        # Bal-snelheid (m/s): alleen voor bal-events, t.o.v. vorig bal-event
        speed = None
        if typ in BALL_EVENTS and loc and prev_ball_loc and prev_ball_t is not None:
            dt = t_now - prev_ball_t
            if dt > 0.05:
                dx = loc[0] - prev_ball_loc[0]
                dy = loc[1] - prev_ball_loc[1]
                dist = math.sqrt(dx * dx + dy * dy)
                speed = round(dist / dt, 2)

        # Cumulatieve Messi-touches
        if plyr == MESSI_NAME:
            cum_messi_touches += 1

        # Tegenstander bij Dribble-event
        opponent_beaten = None
        if typ == "Dribble":
            outcome_name = (e.get("dribble") or {}).get("outcome", {}).get("name", "")
            if outcome_name == "Complete":
                # Zoek de tegenovergestelde "Dribbled Past" via related_events
                for rid in e.get("related_events", []):
                    rel = events_by_id.get(rid)
                    if rel and type_name(rel) == "Dribbled Past":
                        opp_player = rel.get("player") or {}
                        opp_team   = team_name(rel)
                        opponent_beaten = {
                            "id":         opp_player.get("id"),
                            "name":       opp_player.get("name"),
                            "short_name": short_name(opp_player.get("name")),
                            "location":   to_barca_frame(rel.get("location"), opp_team),
                            "team":       opp_team,
                        }
                        break
                opponents_beaten += 1

        # Pass-recipient (vooral interessant bij passes naar Messi)
        pass_recipient = None
        if typ == "Pass":
            rec = (e.get("pass") or {}).get("recipient")
            if rec:
                pass_recipient = {
                    "id":         rec.get("id"),
                    "name":       rec.get("name"),
                    "short_name": short_name(rec.get("name")),
                }

        # Shot-info — end_location heeft 3 dimensies (x,y,z); behoud z apart
        shot_info = None
        if typ == "Shot":
            sh  = e.get("shot") or {}
            end = sh.get("end_location") or []
            shot_info = {
                "xg":           sh.get("statsbomb_xg"),
                "outcome":      (sh.get("outcome") or {}).get("name"),
                "end_location": to_barca_frame(end[:2], team) if len(end) >= 2 else None,
                "end_height":   end[2] if len(end) >= 3 else None,
                "technique":    (sh.get("technique") or {}).get("name"),
                "body_part":    (sh.get("body_part") or {}).get("name"),
            }

        # Dribble-info (zonder outcome opnieuw)
        dribble_info = None
        if typ == "Dribble":
            dr = e.get("dribble") or {}
            dribble_info = {
                "outcome":  (dr.get("outcome") or {}).get("name"),
            }

        # Carry-info: where does the carry end?
        carry_info = None
        if typ == "Carry":
            cr = e.get("carry") or {}
            carry_info = {
                "end_location": to_barca_frame(cr.get("end_location"), team),
            }

        exported_events.append({
            "id":                       e["id"],
            "index":                    e["index"],
            "period":                   e.get("period", 1),
            "timestamp":                e["timestamp"],
            "minute":                   e.get("minute"),
            "second":                   e.get("second"),
            "t_seconds":                round(t_now, 3),
            "type":                     typ,
            "player_id":                player_id(e),
            "player_name":              plyr,
            "player_short":             short_name(plyr),
            "team":                     team_name(e),
            "location":                 loc,
            "duration":                 e.get("duration"),
            "under_pressure":           "under_pressure" in e,
            "inter_event_seconds":      round(inter, 3),
            "ball_speed_mps":           speed,
            "cumulative_messi_touches": cum_messi_touches,
            "opponents_beaten_so_far":  opponents_beaten,
            "pass":                     pass_recipient,
            "dribble":                  dribble_info,
            "opponent_beaten":          opponent_beaten,
            "carry":                    carry_info,
            "shot":                     shot_info,
        })

        prev_t = t_now
        if typ in BALL_EVENTS and loc:
            prev_ball_t   = t_now
            prev_ball_loc = loc

    # ── Barcelona-spelers betrokken in deze possession ─────────────────────────
    barca_players = {}
    for e in poss_events:
        if team_name(e) == BARCA_NAME and player_name(e):
            pid = player_id(e)
            if pid and pid not in barca_players:
                pos = (e.get("position") or {}).get("name")
                barca_players[pid] = {
                    "id":         pid,
                    "name":       player_name(e),
                    "short_name": short_name(player_name(e)),
                    "position":   pos,
                }

    # ── Freeze frame van het schot ─────────────────────────────────────────────
    ff = poss_record.get("freeze_frame") or []
    freeze_frame = [{
        "location":   p.get("location"),
        "player_id":  (p.get("player") or {}).get("id"),
        "name":       (p.get("player") or {}).get("name"),
        "short_name": short_name((p.get("player") or {}).get("name")),
        "position":   (p.get("position") or {}).get("name"),
        "teammate":   p.get("teammate"),
        "actor":      p.get("actor", False),
    } for p in ff]

    # ── Possession-totalen ─────────────────────────────────────────────────────
    duration = exported_events[-1]["t_seconds"] - exported_events[0]["t_seconds"] if len(exported_events) >= 2 else 0
    n_dribbles = sum(1 for e in exported_events if e["type"] == "Dribble")
    n_carries  = sum(1 for e in exported_events if e["type"] == "Carry")
    n_passes   = sum(1 for e in exported_events if e["type"] == "Pass")

    # ── Output-record samenstellen ─────────────────────────────────────────────
    output = {
        "meta": {
            "match_id":     MATCH_ID,
            "possession_id":POSSESSION_ID,
            "match_date":   poss_record["match_date"],
            "competition":  poss_record["competition"],
            "season":       poss_record["season"],
            "home_team":    poss_record["home_team"],
            "away_team":    poss_record["away_team"],
            "score":        f"{poss_record['home_score']}-{poss_record['away_score']}",
            "minute":       exported_events[0]["minute"] if exported_events else None,
            "duration_seconds": round(duration, 3),
            "n_events":     len(exported_events),
            "n_dribbles":   n_dribbles,
            "n_carries":    n_carries,
            "n_passes":     n_passes,
            "messi_touches_total":     cum_messi_touches,
            "opponents_beaten_total":  opponents_beaten,
            "shot_xg":      shot_info["xg"] if shot_info else None,
            "shot_outcome": shot_info["outcome"] if shot_info else None,
            "scorer":       next((e["player_name"] for e in exported_events
                                  if e["type"] == "Shot"), None),
            "pitch": {"length": PITCH_LENGTH, "width": PITCH_WIDTH},
        },
        "barca_players": list(barca_players.values()),
        "events":        exported_events,
        "freeze_frame":  freeze_frame,
    }

    with open(OUTPUT_PATH, "wb") as f:
        f.write(json.dumps(output, indent=2).encode())

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\n✓ Geschreven: {OUTPUT_PATH}  ({size_kb:.1f} KB)")
    print(f"  Events: {len(exported_events)} | Duur: {duration:.2f}s | "
          f"Messi-touches: {cum_messi_touches} | Opponents beaten: {opponents_beaten}")
    print(f"  Barca-spelers in possession: {len(barca_players)} "
          f"({', '.join(p['short_name'] for p in barca_players.values())})")
    print(f"  Freeze frame: {len(freeze_frame)} spelers")


if __name__ == "__main__":
    main()
