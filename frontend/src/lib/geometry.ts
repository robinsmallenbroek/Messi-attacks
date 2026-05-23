import type { AttackEvent, Location } from "../types";

export const PITCH_LENGTH = 120;
export const PITCH_WIDTH = 80;

/** Find the event that is currently "active" given playback time (seconds). */
export function findActiveEventIndex(events: AttackEvent[], tSeconds: number): number {
  if (events.length === 0) return -1;
  let idx = 0;
  for (let i = 0; i < events.length; i++) {
    if (events[i].t_seconds <= tSeconds) idx = i;
    else break;
  }
  return idx;
}

/** Interpolate ball location across event boundaries.
 * Between two ball-events, linearly move the ball; between non-ball events,
 * hold the last known ball location.
 */
const BALL_EVENT_TYPES = new Set([
  "Pass", "Ball Receipt*", "Carry", "Dribble", "Shot",
  "Interception", "Ball Recovery", "Clearance", "Miscontrol", "Goal Keeper", "Block",
]);

export function isBallEvent(e: AttackEvent): boolean {
  return BALL_EVENT_TYPES.has(e.type);
}

export function interpolateBall(events: AttackEvent[], tSeconds: number): Location | null {
  // Find previous ball-event and next ball-event around t
  let prev: AttackEvent | null = null;
  let next: AttackEvent | null = null;
  for (const e of events) {
    if (!isBallEvent(e) || !e.location) continue;
    if (e.t_seconds <= tSeconds) {
      prev = e;
    } else if (next === null) {
      next = e;
      break;
    }
  }
  if (!prev) return next?.location ?? null;
  if (!next || !prev.location || !next.location) return prev.location ?? null;

  const span = next.t_seconds - prev.t_seconds;
  if (span <= 0) return prev.location;
  const t = (tSeconds - prev.t_seconds) / span;
  // Use carry.end_location if prev is a Carry (the ball moves continuously during a carry)
  const end =
    prev.type === "Carry" && prev.carry?.end_location
      ? prev.carry.end_location
      : next.location;
  return [
    prev.location[0] + (end[0] - prev.location[0]) * t,
    prev.location[1] + (end[1] - prev.location[1]) * t,
  ];
}

/** Pitch coordinate → SVG normalized (viewBox is "0 0 120 80"). */
export function pitchX(x: number): number {
  return x;
}
export function pitchY(y: number): number {
  return y;
}

/** Map a t_seconds value to a timeline x position given a total duration and width. */
export function timelineX(tSeconds: number, totalDuration: number, width: number): number {
  return (tSeconds / totalDuration) * width;
}
