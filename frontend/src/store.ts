import { create } from "zustand";
import type { PlaybackMode } from "./types";

/** Two independent layers on top of the basis-viz.  Both start ON.
 *  See LAYERS.md (or the comment in AttackScene.tsx) for the layer ownership
 *  table: basis / hoe / wanneer. */
export interface LensState {
  hoe: boolean;
  wanneer: boolean;
}

interface PlaybackState {
  mode: PlaybackMode;
  // progress 0..1 along the attack
  progress: number;
  isPaused: boolean;
  lens: LensState;
  setMode: (m: PlaybackMode) => void;
  setProgress: (p: number) => void;
  togglePause: () => void;
  setPaused: (b: boolean) => void;
  reset: () => void;
  toggleHoe: () => void;
  toggleWanneer: () => void;
}

export const usePlayback = create<PlaybackState>((set) => ({
  mode: "cinematic",
  progress: 0,
  // Start paused so the intro overlay can be read.  First Spacebar / click
  // begins playback.  Scroll-mode never reads this flag.
  isPaused: true,
  // Both lenses on by default — the viz shows its full reading.
  lens: { hoe: true, wanneer: true },
  setMode: (mode) => set({ mode, progress: 0, isPaused: mode === "cinematic" }),
  setProgress: (progress) => set({ progress: Math.max(0, Math.min(1, progress)) }),
  togglePause: () => set((s) => ({ isPaused: !s.isPaused })),
  setPaused: (isPaused) => set({ isPaused }),
  reset: () => set({ progress: 0, isPaused: true }),
  toggleHoe: () => set((s) => ({ lens: { ...s.lens, hoe: !s.lens.hoe } })),
  toggleWanneer: () => set((s) => ({ lens: { ...s.lens, wanneer: !s.lens.wanneer } })),
}));
