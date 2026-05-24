import type { StatPercentiles } from "../types";

/** Linear-interpolated percentile of `value` within the stored distribution.
 *  Returns 0..100.  Uses min, p10, p25, p50, p75, p90, p95, p99, max anchors.
 *  Approximate but good enough for "krapper dan X% van Barcelona-schoten".
 */
export function percentileOf(value: number, stats: StatPercentiles): number {
  const pts: { p: number; v: number }[] = [];
  const add = (p: number, v: number | null | undefined) => {
    if (v !== null && v !== undefined) pts.push({ p, v });
  };
  add(0,   stats.min);
  add(10,  stats.p10);
  add(25,  stats.p25);
  add(50,  stats.p50);
  add(75,  stats.p75);
  add(90,  stats.p90);
  add(95,  stats.p95);
  add(99,  stats.p99);
  add(100, stats.max);

  if (pts.length < 2) return 50;

  if (value <= pts[0].v)                return pts[0].p;
  if (value >= pts[pts.length - 1].v)   return pts[pts.length - 1].p;

  for (let i = 0; i < pts.length - 1; i++) {
    if (value >= pts[i].v && value <= pts[i + 1].v) {
      const span = pts[i + 1].v - pts[i].v;
      if (span === 0) return pts[i].p;
      const local = (value - pts[i].v) / span;
      return pts[i].p + local * (pts[i + 1].p - pts[i].p);
    }
  }
  return 50;
}

/** Returns the rank as "tighter/lower than X% of the distribution".
 *  Used when a SMALLER value means more remarkable (e.g. tighter space). */
export function tightnessRank(value: number, stats: StatPercentiles): number {
  return Math.round(100 - percentileOf(value, stats));
}

/** Returns the rank as "higher than X% of the distribution".
 *  Used when a LARGER value means more remarkable. */
export function aboveRank(value: number, stats: StatPercentiles): number {
  return Math.round(percentileOf(value, stats));
}
