import type { AttackData, AttackEvent, Location } from "../types";
import { C, FONT } from "../lib/theme";
import { isBallEvent } from "../lib/geometry";

interface Props {
  data: AttackData;
  x: number;
  y: number;
  width: number;
  height: number;
  realTime: number;
  /** 0..1 progress within the current phase — needed for hold-phase choreography */
  phaseLabel: string;
  phaseProgress: number;
}

function makeMappers(x: number, y: number, width: number, height: number) {
  return {
    px: (px: number) => x + (px / 120) * width,
    py: (py: number) => y + (py / 80) * height,
  };
}

function FieldLines({ px, py, x, y, width, height }:
  { px: (n:number)=>number; py:(n:number)=>number; x:number; y:number; width:number; height:number }) {
  const stroke = C.lineMuted;
  return (
    <g stroke={stroke} strokeWidth={0.6} fill="none">
      <rect x={x} y={y} width={width} height={height} fill={C.bgSoft} stroke={stroke}/>
      <line x1={px(60)} y1={py(0)} x2={px(60)} y2={py(80)} />
      <circle cx={px(60)} cy={py(40)} r={(width / 120) * 9.15} />
      <circle cx={px(60)} cy={py(40)} r={1.2} fill={stroke} />
      <rect x={px(0)}   y={py(18)} width={px(18) - px(0)}    height={py(62) - py(18)} />
      <rect x={px(0)}   y={py(30)} width={px(6) - px(0)}     height={py(50) - py(30)} />
      <circle cx={px(12)} cy={py(40)} r={1} fill={stroke} />
      <rect x={px(102)} y={py(18)} width={px(120) - px(102)} height={py(62) - py(18)} />
      <rect x={px(114)} y={py(30)} width={px(120) - px(114)} height={py(50) - py(30)} />
      <circle cx={px(108)} cy={py(40)} r={1} fill={stroke} />
      <line x1={px(0)}   y1={py(36)} x2={px(0)}   y2={py(44)} stroke={C.line} strokeWidth={1.2}/>
      <line x1={px(120)} y1={py(36)} x2={px(120)} y2={py(44)} stroke={C.line} strokeWidth={1.2}/>
    </g>
  );
}

function colorFor(e: AttackEvent): string {
  if (e.player_short === "Messi") return C.messi;
  if (e.team === "Barcelona") return C.barca;
  return C.opp;
}

function smooth(t: number): number {
  const c = Math.max(0, Math.min(1, t));
  return c * c * (3 - 2 * c);
}

function lerpColor(a: string, b: string, t: number): string {
  const ah = a.replace("#", ""), bh = b.replace("#", "");
  const ar = parseInt(ah.slice(0, 2), 16), ag = parseInt(ah.slice(2, 4), 16), ab = parseInt(ah.slice(4, 6), 16);
  const br = parseInt(bh.slice(0, 2), 16), bg = parseInt(bh.slice(2, 4), 16), bb = parseInt(bh.slice(4, 6), 16);
  const r = Math.round(ar + (br - ar) * t);
  const g = Math.round(ag + (bg - ag) * t);
  const blue = Math.round(ab + (bb - ab) * t);
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${blue.toString(16).padStart(2, "0")}`;
}

/** Interpolate the ball position at attack-time t.
 *
 *  Model:  the ball is always "in" some event's window.  Each ball-event e
 *  occupies the time-range [e.t_seconds, nextBallEvent.t_seconds).  Within
 *  that range:
 *
 *    • Carry:        ball moves from e.location to e.carry.end_location
 *                    over min(e.duration, nextEvent − e.t_seconds), then
 *                    travels to nextEvent.location over the remainder.
 *    • Pass:         ball travels from e.location to next.location over the
 *                    full window (a pass in flight).
 *    • Other (Ball Receipt, Dribble, Shot, Interception, Block, ...):
 *                    ball sits at e.location.  If a later ball-event exists,
 *                    we still travel toward it during the gap, because the
 *                    real ball never teleports.
 */
function ballAt(events: AttackEvent[], t: number): Location | null {
  const ballEvents = events.filter(e => isBallEvent(e) && e.location);
  if (ballEvents.length === 0) return null;
  if (t <= ballEvents[0].t_seconds) return ballEvents[0].location;

  for (let i = 0; i < ballEvents.length; i++) {
    const e = ballEvents[i];
    const next = ballEvents[i + 1];
    const windowEnd = next ? next.t_seconds : (e.t_seconds + (e.duration ?? 0));

    if (t < e.t_seconds || t >= windowEnd) continue;

    // We are inside event e's time window.
    if (e.type === "Carry" && e.carry?.end_location) {
      const carryDur = e.duration ?? 0;
      const carryEndsAt = Math.min(e.t_seconds + carryDur, windowEnd);
      if (t < carryEndsAt) {
        const local = (t - e.t_seconds) / Math.max(0.001, carryEndsAt - e.t_seconds);
        return [
          e.location![0] + (e.carry.end_location[0] - e.location![0]) * local,
          e.location![1] + (e.carry.end_location[1] - e.location![1]) * local,
        ];
      }
      // Carry finished, ball drifts toward next event's start location.
      if (next?.location) {
        const drift = (t - carryEndsAt) / Math.max(0.001, windowEnd - carryEndsAt);
        return [
          e.carry.end_location[0] + (next.location[0] - e.carry.end_location[0]) * drift,
          e.carry.end_location[1] + (next.location[1] - e.carry.end_location[1]) * drift,
        ];
      }
      return e.carry.end_location;
    }

    // Non-carry: travel toward the next event's location over the window.
    if (next?.location) {
      const local = (t - e.t_seconds) / Math.max(0.001, windowEnd - e.t_seconds);
      return [
        e.location![0] + (next.location[0] - e.location![0]) * local,
        e.location![1] + (next.location[1] - e.location![1]) * local,
      ];
    }
    return e.location;
  }

  // t after the last ball-event window: stay at the last known position.
  const last = ballEvents[ballEvents.length - 1];
  if (last.type === "Carry" && last.carry?.end_location) return last.carry.end_location;
  return last.location;
}

function dist(a: Location, b: Location): number {
  const dx = a[0] - b[0], dy = a[1] - b[1];
  return Math.sqrt(dx * dx + dy * dy);
}

export default function Pitch({ data, x, y, width, height, realTime, phaseLabel, phaseProgress }: Props) {
  const { px, py } = makeMappers(x, y, width, height);
  const events = data.events;
  const freeze = data.freeze_frame;

  // Shot location (= Messi's position at the shot)
  const shotEvent = events.find(e => e.type === "Shot");
  const shotLoc: Location | null = shotEvent?.location ?? null;
  const shotEnd: Location | null = shotEvent?.shot?.end_location ?? null;

  // Are we revealing the freeze frame?  Yes during shot-hold AND after.
  const inShotHold = phaseLabel === "shot-hold";
  const postShot = realTime >= (shotEvent?.t_seconds ?? Infinity);
  // The reveal "global progress": 0 during attack, 0..1 during shot-hold, 1 after
  const revealProgress = inShotHold ? phaseProgress : (postShot ? 1 : 0);

  // ── Dribble beats (same as iteration 5) ────────────────────────────────────
  type Beat = { dribbleT: number; location: Location; label: string; fromMessi: Location };
  const beats: Beat[] = [];
  events.forEach((e, i) => {
    if (e.type !== "Dribble" || !e.opponent_beaten || !e.opponent_beaten.location) return;
    let fromMessi: Location | null = null;
    for (let j = i - 1; j >= 0; j--) {
      const p = events[j];
      if (p.player_short === "Messi" && p.location) { fromMessi = p.location; break; }
    }
    beats.push({
      dribbleT: e.t_seconds, location: e.opponent_beaten.location,
      label: e.opponent_beaten.short_name, fromMessi: fromMessi ?? e.opponent_beaten.location,
    });
  });
  function beatFor(loc: Location, label: string): Beat | null {
    for (const b of beats) {
      if (b.label === label &&
          Math.round(b.location[0]) === Math.round(loc[0]) &&
          Math.round(b.location[1]) === Math.round(loc[1])) return b;
    }
    return null;
  }

  // ── Ball trail ─────────────────────────────────────────────────────────────
  type Segment = { x1:number; y1:number; x2:number; y2:number; tStart:number; tEnd:number; emphasis:number };
  const segments: Segment[] = [];
  let prev: AttackEvent | null = null;
  for (const e of events) {
    if (!isBallEvent(e) || !e.location) continue;
    if (prev && prev.location) {
      if (prev.type === "Carry" && prev.carry?.end_location) {
        const carryDur = prev.duration ?? 0;
        segments.push({
          x1: px(prev.location[0]), y1: py(prev.location[1]),
          x2: px(prev.carry.end_location[0]), y2: py(prev.carry.end_location[1]),
          tStart: prev.t_seconds, tEnd: prev.t_seconds + carryDur, emphasis: 0.55,
        });
        segments.push({
          x1: px(prev.carry.end_location[0]), y1: py(prev.carry.end_location[1]),
          x2: px(e.location[0]), y2: py(e.location[1]),
          tStart: prev.t_seconds + carryDur, tEnd: e.t_seconds, emphasis: 0.35,
        });
      } else {
        segments.push({
          x1: px(prev.location[0]), y1: py(prev.location[1]),
          x2: px(e.location[0]), y2: py(e.location[1]),
          tStart: prev.t_seconds, tEnd: e.t_seconds, emphasis: 0.45,
        });
      }
    }
    prev = e;
  }

  const ballPos = ballAt(events, realTime);

  // ── Event-derived marks ────────────────────────────────────────────────────
  type LocMark = {
    key: string; loc: Location; label: string; color: string;
    isMessi: boolean; isOpponent: boolean; firstSeen: number;
  };
  const marks = new Map<string, LocMark>();
  events.forEach((e) => {
    if (!e.location) return;
    const k = `${e.player_short}@${Math.round(e.location[0])},${Math.round(e.location[1])}`;
    if (!marks.has(k)) {
      marks.set(k, {
        key: k, loc: e.location,
        label: e.player_short, color: colorFor(e),
        isMessi: e.player_short === "Messi",
        isOpponent: e.team !== "Barcelona",
        firstSeen: e.t_seconds,
      });
    }
  });
  events.forEach((e) => {
    const opp = e.opponent_beaten;
    if (!opp || !opp.location) return;
    const k = `${opp.short_name}@${Math.round(opp.location[0])},${Math.round(opp.location[1])}`;
    if (!marks.has(k)) {
      marks.set(k, {
        key: k, loc: opp.location, label: opp.short_name, color: C.opp,
        isMessi: false, isOpponent: true, firstSeen: e.t_seconds - 0.3,
      });
    }
  });

  // ── Freeze-frame: sort by distance to Messi for stagger order ──────────────
  // Closer = revealed earlier.  Tells the story of how packed it was around Messi.
  const ffSorted = [...freeze].sort((a, b) =>
    (shotLoc ? dist(a.location, shotLoc) : 0) - (shotLoc ? dist(b.location, shotLoc) : 0)
  );

  // For ghost-lines: each freeze player who also had events gets a line from
  // their last event-location to their freeze position.  Stored by short_name.
  const lastEventLocBySN = new Map<string, Location>();
  for (const e of events) {
    if (!e.location || !e.player_short) continue;
    if (e.player_short === "Messi") continue;  // skip — Messi's event ≈ shot loc
    lastEventLocBySN.set(e.player_short, e.location);
  }

  // Closest opponent to Messi — for the "space bubble" radius
  const closestOpp = ffSorted.find(p => !p.teammate && p.position !== "Goalkeeper");
  const messiSpaceR = shotLoc && closestOpp ? dist(shotLoc, closestOpp.location) : null;

  return (
    <g fontFamily={FONT.sans}>
      <FieldLines px={px} py={py} x={x} y={y} width={width} height={height} />

      {/* Trail */}
      <g opacity={inShotHold ? 0.55 : 1}>
        {segments.map((s, i) => {
          if (realTime <= s.tStart) return null;
          const span = s.tEnd - s.tStart;
          const local = span > 0 ? Math.min(1, (realTime - s.tStart) / span) : 1;
          const ex = s.x1 + (s.x2 - s.x1) * local;
          const ey = s.y1 + (s.y2 - s.y1) * local;
          return (
            <line key={i} x1={s.x1} y1={s.y1} x2={ex} y2={ey}
                  stroke={C.messi} strokeWidth={1.7} opacity={s.emphasis}
                  strokeLinecap="round" />
          );
        })}
      </g>

      {/* Dribble effect ring */}
      <g>
        {beats.map((b, i) => {
          const enter = b.dribbleT - 0.5;
          const exit  = b.dribbleT + 0.3;
          if (realTime < enter) return null;
          const t = Math.max(0, Math.min(1, (realTime - enter) / (exit - enter)));
          const r = 4 + t * 18;
          const op = 0.7 * (1 - Math.abs(t - 0.45) * 1.8);
          if (op <= 0) return null;
          return (
            <circle key={i} cx={px(b.location[0])} cy={py(b.location[1])}
                    r={r} fill="none" stroke={C.opp} strokeWidth={1.4}
                    opacity={Math.max(0, op)} />
          );
        })}
      </g>

      {/* Event-derived markers — fade out a bit during freeze reveal to give
          space to the freeze-frame layer (which uses the *same* people in some
          cases but at their final positions). */}
      <g opacity={1 - revealProgress * 0.55}>
        {Array.from(marks.values()).map((m) => {
          const fadeIn = smooth((realTime - m.firstSeen) / 0.35);
          if (fadeIn <= 0) return null;
          const beat = m.isOpponent ? beatFor(m.loc, m.label) : null;
          let renderLoc = m.loc;
          let renderColor = m.color;
          let beatProgress = 0;
          if (beat) {
            beatProgress = smooth((realTime - beat.dribbleT) / 0.35);
            if (beatProgress > 0) {
              const dx = beat.location[0] - beat.fromMessi[0];
              const dy = beat.location[1] - beat.fromMessi[1];
              const len = Math.sqrt(dx*dx + dy*dy) || 1;
              const shift = 0.6 * beatProgress;
              renderLoc = [beat.location[0] + (dx/len) * shift,
                           beat.location[1] + (dy/len) * shift];
              renderColor = lerpColor(C.opp, "#5e2728", beatProgress);
            }
          }
          const cx = px(renderLoc[0]);
          const cy = py(renderLoc[1]);
          const r  = m.isMessi ? 5.5 : (m.isOpponent ? 3.5 : 4);
          const opacity = fadeIn * (1 - beatProgress * 0.45);
          return (
            <g key={m.key} opacity={opacity}>
              {m.isMessi && (
                <circle cx={cx} cy={cy} r={11} fill={C.messi} opacity={0.10} />
              )}
              <circle cx={cx} cy={cy} r={r} fill={renderColor}
                      stroke={C.bg} strokeWidth={1} />
              <text x={cx + r + 4} y={cy + 3.5} fill={renderColor}
                    fontSize={m.isMessi ? 12 : 10}
                    fontWeight={m.isMessi ? 600 : 400}
                    style={{ textDecoration: beatProgress > 0.5 ? "line-through" : "none",
                             textDecorationColor: C.oppFade,
                             textDecorationThickness: "1px" }}>
                {m.label}
              </text>
            </g>
          );
        })}
      </g>

      {/* Beat label flash */}
      <g>
        {beats.map((b, i) => {
          const flashWindow = 0.7;
          const local = (realTime - b.dribbleT + 0.1) / flashWindow;
          if (local < 0 || local > 1) return null;
          const op = local < 0.4 ? local / 0.4 : (1 - local) / 0.6;
          if (op <= 0) return null;
          return (
            <g key={i} opacity={Math.min(1, op)}>
              <text x={px(b.location[0]) + 14} y={py(b.location[1]) - 8}
                    fill={C.opp} fontSize={11} fontWeight={600}
                    letterSpacing="0.1em">
                × {b.label.toUpperCase()}
              </text>
            </g>
          );
        })}
      </g>

      {/* ── FREEZE FRAME REVEAL ────────────────────────────────────────────────
          Triggered during shot-hold (realTime is fixed at shot moment).
          Players appear staggered, closest to Messi first.  Each gets a ghost
          line from its event-location if applicable. */}
      {revealProgress > 0 && shotLoc && (
        <g>
          {/* Messi space bubble — radius = distance to closest non-keeper opponent */}
          {messiSpaceR !== null && (
            <g opacity={smooth(revealProgress * 3) * 0.55}>
              <circle cx={px(shotLoc[0])} cy={py(shotLoc[1])}
                      r={(messiSpaceR / 120) * width}
                      fill="none" stroke={C.messi} strokeWidth={0.8}
                      strokeDasharray="2 3" opacity={0.7} />
              {/* Radius label, positioned beside the bubble */}
              <text x={px(shotLoc[0]) + (messiSpaceR / 120) * width + 6}
                    y={py(shotLoc[1]) + 3} fill={C.messiSoft.length === 9 ? C.messi : C.messi}
                    fontSize={10} letterSpacing="0.08em" opacity={0.85}>
                {messiSpaceR.toFixed(1)} M TOT DICHTSTBIJZIJNDE
              </text>
            </g>
          )}

          {/* Shot trajectory — Messi → end_location (if known) */}
          {shotEnd && revealProgress > 0.3 && (
            <g opacity={Math.min(1, (revealProgress - 0.3) / 0.3)}>
              <line x1={px(shotLoc[0])} y1={py(shotLoc[1])}
                    x2={px(shotEnd[0])} y2={py(shotEnd[1])}
                    stroke={C.shot} strokeWidth={1.6}
                    strokeDasharray="3 2" />
              <circle cx={px(shotEnd[0])} cy={py(shotEnd[1])} r={3.5}
                      fill={C.shot} />
            </g>
          )}

          {/* Freeze-frame players, staggered */}
          {ffSorted.map((p, i) => {
            // Stagger: each player appears at a fraction of the reveal progress.
            // Reserve the last 30% for the shot trajectory to read.
            const usableReveal = 0.7;
            const start = (i / Math.max(1, ffSorted.length)) * usableReveal;
            const local = smooth((revealProgress - start) / 0.18);
            if (local <= 0) return null;

            const isKeeper = p.position === "Goalkeeper";
            const color = p.teammate ? C.barca : (isKeeper ? C.shot : C.opp);
            const r = isKeeper ? 4.5 : (p.teammate ? 4 : 4);

            // Ghost line from last event-location (if this player had events)
            const prevLoc = p.short_name ? lastEventLocBySN.get(p.short_name) : null;

            return (
              <g key={`ff-${i}`} opacity={local}>
                {prevLoc && (
                  <line x1={px(prevLoc[0])} y1={py(prevLoc[1])}
                        x2={px(p.location[0])} y2={py(p.location[1])}
                        stroke={color} strokeWidth={0.5}
                        strokeDasharray="1 2" opacity={0.5} />
                )}
                <circle cx={px(p.location[0])} cy={py(p.location[1])} r={r}
                        fill={color} stroke={C.bg} strokeWidth={1} />
                <text x={px(p.location[0]) + r + 4}
                      y={py(p.location[1]) + 3.5}
                      fill={color} fontSize={10}
                      fontWeight={p.teammate ? 500 : 400}>
                  {p.short_name}
                  {isKeeper && <tspan fill={C.textFade} fontSize={9}> · keeper</tspan>}
                </text>
              </g>
            );
          })}

          {/* Messi himself — extra glow during reveal */}
          <g opacity={smooth(revealProgress * 2)}>
            <circle cx={px(shotLoc[0])} cy={py(shotLoc[1])} r={18}
                    fill={C.messi} opacity={0.10} />
            <circle cx={px(shotLoc[0])} cy={py(shotLoc[1])} r={9}
                    fill={C.messi} opacity={0.20} />
            <circle cx={px(shotLoc[0])} cy={py(shotLoc[1])} r={6}
                    fill={C.messi} stroke={C.bg} strokeWidth={1.2} />
            <text x={px(shotLoc[0]) + 10} y={py(shotLoc[1]) + 3.5}
                  fill={C.messi} fontSize={13} fontWeight={700}>
              Messi
            </text>
          </g>
        </g>
      )}

      {/* Live ball — hide once we're in the freeze-frame reveal so the shot
          dot and freeze frame can take center stage */}
      {ballPos && revealProgress < 0.15 && (
        <g opacity={1 - revealProgress * 6}>
          <circle cx={px(ballPos[0])} cy={py(ballPos[1])} r={6}
                  fill={C.messi} opacity={0.25} />
          <circle cx={px(ballPos[0])} cy={py(ballPos[1])} r={2.6}
                  fill={C.shot} />
        </g>
      )}

      <g opacity={0.45}>
        <text x={x + width - 4} y={y + height + 14} fill={C.textFade} fontSize={9}
              textAnchor="end" letterSpacing="0.1em">
          AANVALSRICHTING →
        </text>
      </g>
    </g>
  );
}

export function pitchBallPosition(data: AttackData, x: number, y: number,
                                   width: number, height: number, realTime: number): { x: number; y: number } | null {
  const { px, py } = makeMappers(x, y, width, height);
  const pos = ballAt(data.events, realTime);
  if (!pos) return null;
  return { x: px(pos[0]), y: py(pos[1]) };
}
