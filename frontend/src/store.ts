import { create } from "zustand";
import type { PlaybackMode } from "./types";

interface PlaybackState {
  mode: PlaybackMode;
  // progress 0..1 along the attack
  progress: number;
  isPaused: boolean;
  setMode: (m: PlaybackMode) => void;
  setProgress: (p: number) => void;
  togglePause: () => void;
  setPaused: (b: boolean) => void;
  reset: () => void;
}

export const usePlayback = create<PlaybackState>((set) => ({
  mode: "cinematic",
  progress: 0,
  // Start paused so the intro overlay can be read.  First Spacebar / click
  // begins playback.  Scroll-mode never reads this flag.
  isPaused: true,
  setMode: (mode) => set({ mode, progress: 0, isPaused: mode === "cinematic" }),
  setProgress: (progress) => set({ progress: Math.max(0, Math.min(1, progress)) }),
  togglePause: () => set((s) => ({ isPaused: !s.isPaused })),
  setPaused: (isPaused) => set({ isPaused }),
  reset: () => set({ progress: 0, isPaused: true }),
}));
