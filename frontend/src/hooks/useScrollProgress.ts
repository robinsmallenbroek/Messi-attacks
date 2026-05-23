import { useEffect, RefObject } from "react";
import { usePlayback } from "../store";

/** When active, listens to window scroll and maps the position of `ref` within
 *  the viewport to progress (0..1).  Uses passive scroll listening for perf.
 *  Mapping: progress = clamp((scrolled within container) / (container - viewport), 0, 1)
 */
export function useScrollProgress(active: boolean, ref: RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    if (!active) return;
    const el = ref.current;
    if (!el) return;

    let rafPending = false;

    const update = () => {
      rafPending = false;
      const rect = el.getBoundingClientRect();
      const containerH = el.offsetHeight;
      const viewportH  = window.innerHeight;
      const scrollableSpan = Math.max(1, containerH - viewportH);
      // -rect.top is how far we've scrolled past the top of the container.
      const scrolled = Math.max(0, -rect.top);
      const p = Math.max(0, Math.min(1, scrolled / scrollableSpan));
      usePlayback.getState().setProgress(p);
    };

    // Throttle to one update per animation frame.
    const onScroll = () => {
      if (!rafPending) {
        rafPending = true;
        requestAnimationFrame(update);
      }
    };

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [active, ref]);
}
