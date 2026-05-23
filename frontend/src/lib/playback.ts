// Cinematic phase mapping.
//
// Each phase maps a stretch of WALL-CLOCK (playback) seconds to a stretch
// of REAL attack-time seconds.  Slope (realDelta / playDelta) controls pace.
//
// Why hand-tuned and not linear?  A 10-second attack played at 2.5× slowdown
// would be 25s of constant tempo — that's a metronome, not cinema.  The
// pacing here mirrors what we want the viewer to feel: the long carry asks
// for breath, the dribble asks for a stop, the shot asks for silence.

export interface Phase {
  startReal: number;   // attack-time start (seconds)
  endReal:   number;   // attack-time end
  playDuration: number; // wall-clock seconds this phase consumes
  label?: string;       // for debugging
}

export const PHASES: Phase[] = [
  { startReal:  0.00, endReal:  0.00, playDuration: 0.5, label: "intro-hold" },
  { startReal:  0.00, endReal:  5.56, playDuration: 8.0, label: "alexis-carry" },
  { startReal:  5.56, endReal:  5.56, playDuration: 1.0, label: "pass-arrival-hold" },
  { startReal:  5.56, endReal:  7.12, playDuration: 3.0, label: "messi-receives" },
  { startReal:  7.12, endReal:  9.19, playDuration: 4.5, label: "messi-carries-to-dribble" },
  { startReal:  9.19, endReal:  9.19, playDuration: 0.8, label: "dribble-beat-hold" },
  { startReal:  9.19, endReal: 10.22, playDuration: 2.0, label: "shot-approach" },
  { startReal: 10.22, endReal: 10.22, playDuration: 1.2, label: "shot-hold" },
];

export const TOTAL_PLAY_DURATION = PHASES.reduce((a, p) => a + p.playDuration, 0);

/** Map progress (0..1 along the playback) to attack-real-time seconds. */
export function progressToRealTime(progress: number): number {
  const p = Math.max(0, Math.min(1, progress));
  const playTime = p * TOTAL_PLAY_DURATION;
  let acc = 0;
  for (const phase of PHASES) {
    if (playTime <= acc + phase.playDuration) {
      const local = phase.playDuration > 0 ? (playTime - acc) / phase.playDuration : 0;
      return phase.startReal + local * (phase.endReal - phase.startReal);
    }
    acc += phase.playDuration;
  }
  return PHASES[PHASES.length - 1].endReal;
}

/** Inverse: real-time → progress (used for jumping to a moment). */
export function realTimeToProgress(realTime: number): number {
  let acc = 0;
  for (const phase of PHASES) {
    const phaseSpan = phase.endReal - phase.startReal;
    if (realTime <= phase.endReal) {
      const local = phaseSpan > 0 ? (realTime - phase.startReal) / phaseSpan : 0;
      return (acc + local * phase.playDuration) / TOTAL_PLAY_DURATION;
    }
    acc += phase.playDuration;
  }
  return 1;
}

/** Return the current phase label for debugging / UI hints. */
export function currentPhase(progress: number): Phase {
  return getPhaseInfo(progress).phase;
}

/** Return the current phase AND the 0..1 local progress within it.
 *  Used by hold-phase visual effects (freeze-frame reveal) where attack-real-time
 *  is frozen but we still want a time source for choreography. */
export function getPhaseInfo(progress: number): { phase: Phase; phaseProgress: number } {
  const p = Math.max(0, Math.min(1, progress));
  const playTime = p * TOTAL_PLAY_DURATION;
  let acc = 0;
  for (const phase of PHASES) {
    if (playTime <= acc + phase.playDuration) {
      const local = phase.playDuration > 0 ? (playTime - acc) / phase.playDuration : 1;
      return { phase, phaseProgress: local };
    }
    acc += phase.playDuration;
  }
  return { phase: PHASES[PHASES.length - 1], phaseProgress: 1 };
}
