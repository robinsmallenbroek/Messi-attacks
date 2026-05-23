import type { AttackData } from "../types";
import { usePlayback } from "../store";
import { C, FONT } from "../lib/theme";

/** Intro overlay — shows while progress = 0 and we're paused, in cinematic mode.
 *  Disappears on first space / click.  Gives the viewer a moment to read context
 *  before the 21-second play.  No automatic timer — agency over the start. */
export function IntroOverlay({ data }: { data: AttackData }) {
  const progress = usePlayback((s) => s.progress);
  const isPaused = usePlayback((s) => s.isPaused);
  const mode     = usePlayback((s) => s.mode);
  const togglePause = usePlayback((s) => s.togglePause);

  const visible = mode === "cinematic" && progress === 0 && isPaused;
  if (!visible) return null;

  const m = data.meta;

  return (
    <div onClick={togglePause}
         style={{
           position: "fixed", inset: 0, zIndex: 50,
           background: "rgba(10, 14, 22, 0.78)",
           backdropFilter: "blur(2px)",
           display: "flex", alignItems: "center", justifyContent: "center",
           cursor: "pointer",
           fontFamily: FONT.sans,
           animation: "fade-in 0.6s ease both",
         }}>
      <style>{`
        @keyframes fade-in { from { opacity: 0 } to { opacity: 1 } }
        @keyframes pulse-soft { 0%,100% { opacity: 0.6 } 50% { opacity: 1 } }
      `}</style>

      <div style={{ maxWidth: 640, padding: "0 32px", textAlign: "left" }}>
        <div style={{ color: C.textDim, fontSize: 11, letterSpacing: "0.2em",
                      textTransform: "uppercase", marginBottom: 18 }}>
          Lens 02 · Individuele virtuositeit
        </div>

        <h1 style={{ fontFamily: FONT.serif, fontWeight: 300, fontSize: 56,
                     letterSpacing: "-0.015em", margin: 0, lineHeight: 1.05,
                     color: C.text }}>
          <span style={{ color: C.messi, fontWeight: 400 }}>Messi</span> tegen<br/>
          Real Zaragoza
        </h1>

        <div style={{ color: C.textDim, fontSize: 14, marginTop: 18,
                      lineHeight: 1.55, maxWidth: 540 }}>
          {m.match_date} · La Liga {m.season} · minuut {m.minute}<br/>
          Een aanval van {m.duration_seconds.toFixed(1)} seconden,
          {" "}{m.n_events} events, eindigend in een doelpunt.
        </div>

        <div style={{ color: C.textFade, fontSize: 13, marginTop: 26,
                      lineHeight: 1.6, maxWidth: 540, fontStyle: "italic" }}>
          De video laat zien wat hij doet. Deze visualisatie laat zien
          wat de video niet ziet — het ritme, de ruimte, en de spelers
          om hem heen op het moment dat hij schoot.
        </div>

        <div style={{ marginTop: 48, display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{
            color: C.messi, fontSize: 12, letterSpacing: "0.22em",
            textTransform: "uppercase", fontWeight: 500,
            animation: "pulse-soft 2s ease-in-out infinite",
          }}>
            Klik of spatie · start
          </div>
        </div>
      </div>
    </div>
  );
}

/** Outro overlay — appears after the freeze-frame reveal finishes.
 *  Sits as a band BELOW the visualization (not fullscreen) so the freeze
 *  frame stays on screen as the takeaway is read. */
export function OutroPanel({ data }: { data: AttackData }) {
  const progress = usePlayback((s) => s.progress);
  const mode     = usePlayback((s) => s.mode);
  const reset    = usePlayback((s) => s.reset);

  // Show only when the playback has fully completed.
  const visible = mode === "cinematic" && progress >= 1;
  if (!visible) return null;

  return (
    <div style={{
      paddingLeft: 60, paddingRight: 60, marginTop: 36, maxWidth: 1100,
      animation: "fade-in 0.8s ease 0.2s both",
      fontFamily: FONT.sans,
    }}>
      <div style={{ color: C.textDim, fontSize: 11, letterSpacing: "0.2em",
                    textTransform: "uppercase", marginBottom: 14 }}>
        Wat de data toonde
      </div>
      <div style={{ fontFamily: FONT.serif, fontSize: 22, lineHeight: 1.45,
                    color: C.text, fontWeight: 300, maxWidth: 720 }}>
        Messi schoot van <span style={{ color: C.messi, fontWeight: 400 }}>1.2 meter</span>
        {" "}tot zijn dichtstbijzijnde verdediger — diezelfde Barrios die hij
        één seconde eerder gepasseerd had. Vier verdedigers binnen tien meter.
        Twee teamgenoten te ver om aan te spelen.
        {" "}<span style={{ color: C.textDim, fontStyle: "italic" }}>
          De "solo" was een doelpunt onder druk.
        </span>
      </div>

      <div style={{ marginTop: 28 }}>
        <button onClick={reset}
                style={{
                  background: "transparent",
                  border: `1px solid ${C.line}`,
                  color: C.textDim,
                  padding: "10px 18px",
                  fontFamily: FONT.sans, fontSize: 11,
                  letterSpacing: "0.16em", textTransform: "uppercase",
                  cursor: "pointer",
                  transition: "color 0.2s, border-color 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = C.text;
                  e.currentTarget.style.borderColor = C.textDim;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = C.textDim;
                  e.currentTarget.style.borderColor = C.line;
                }}>
          ↻ Opnieuw zien
        </button>
      </div>
    </div>
  );
}
