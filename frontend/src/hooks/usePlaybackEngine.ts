import { useEffect } from "react";
import { usePlayback } from "../store";
import { TOTAL_PLAY_DURATION } from "../lib/playback";

/** Drives `progress` in the store at 1× wall-clock speed.
 *  Cinematic mode: advances automatically until 1.0, then holds.
 *  Scroll mode: this hook is inert (the scroll handler will drive progress).
 *  Pause: rAF loop runs but does not advance progress.
 */
export function usePlaybackEngine() {
  const mode      = usePlayback((s) => s.mode);
  const isPaused  = usePlayback((s) => s.isPaused);

  useEffect(() => {
    if (mode !== "cinematic") return;

    let raf = 0;
    let last = performance.now();

    const tick = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;
      const { progress, isPaused, setProgress } = usePlayback.getState();
      if (!isPaused && progress < 1) {
        // Advance by dt seconds of wall-clock; full playback is TOTAL_PLAY_DURATION
        const next = Math.min(1, progress + dt / TOTAL_PLAY_DURATION);
        setProgress(next);
      }
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [mode, isPaused]);

  // Spacebar = toggle pause; R = restart
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        e.preventDefault();
        usePlayback.getState().togglePause();
      } else if (e.code === "KeyR") {
        usePlayback.getState().reset();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}
