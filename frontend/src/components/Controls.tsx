import { usePlayback } from "../store";
import { C, FONT } from "../lib/theme";

export default function Controls() {
  const mode      = usePlayback((s) => s.mode);
  const progress  = usePlayback((s) => s.progress);
  const isPaused  = usePlayback((s) => s.isPaused);
  const togglePause = usePlayback((s) => s.togglePause);
  const reset     = usePlayback((s) => s.reset);
  const setMode   = usePlayback((s) => s.setMode);

  const Btn = ({ onClick, active, children }:
    { onClick: () => void; active?: boolean; children: React.ReactNode }) => (
    <button onClick={onClick}
            style={{
              background: active ? C.line : "transparent",
              border: `1px solid ${active ? C.textDim : C.line}`,
              color: active ? C.text : C.textDim,
              padding: "8px 14px",
              fontFamily: FONT.sans,
              fontSize: 11,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              cursor: "pointer",
              transition: "color 0.2s, border-color 0.2s, background 0.2s",
            }}
            onMouseEnter={(e) => {
              if (active) return;
              e.currentTarget.style.color = C.text;
              e.currentTarget.style.borderColor = C.textDim;
            }}
            onMouseLeave={(e) => {
              if (active) return;
              e.currentTarget.style.color = C.textDim;
              e.currentTarget.style.borderColor = C.line;
            }}>
      {children}
    </button>
  );

  // Mode-aware action set.  In scroll mode there's no pause/restart — the
  // browser scroll is the pause.  Showing them would be a lie.
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "center",
                  paddingLeft: 60, marginTop: 24, flexWrap: "wrap" }}>
      <div style={{ display: "flex", gap: 0 }}>
        <Btn onClick={() => { window.scrollTo(0, 0); setMode("cinematic"); }}
             active={mode === "cinematic"}>
          Cinematic
        </Btn>
        <Btn onClick={() => { window.scrollTo(0, 0); setMode("scroll"); }}
             active={mode === "scroll"}>
          Scroll
        </Btn>
      </div>

      {mode === "cinematic" && (
        <>
          <span style={{ width: 12 }} />
          <Btn onClick={togglePause}>
            {progress >= 1 ? "Klaar"
             : isPaused ? "▶ Hervat"
                        : "Pauzeer"}
          </Btn>
          <Btn onClick={reset}>↻ Opnieuw</Btn>
          <span style={{ color: C.textFade, fontSize: 10,
                         letterSpacing: "0.14em", textTransform: "uppercase",
                         fontFamily: FONT.sans, marginLeft: 8 }}>
            Spatie · pauze   ·   R · opnieuw
          </span>
        </>
      )}

      {mode === "scroll" && (
        <span style={{ color: C.textFade, fontSize: 10,
                       letterSpacing: "0.14em", textTransform: "uppercase",
                       fontFamily: FONT.sans, marginLeft: 12 }}>
          Scroll om door de aanval te bewegen
        </span>
      )}
    </div>
  );
}
