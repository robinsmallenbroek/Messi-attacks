import { usePlayback } from "../store";
import { C, FONT } from "../lib/theme";

export default function Controls() {
  const mode      = usePlayback((s) => s.mode);
  const progress  = usePlayback((s) => s.progress);
  const isPaused  = usePlayback((s) => s.isPaused);
  const togglePause = usePlayback((s) => s.togglePause);
  const reset     = usePlayback((s) => s.reset);
  const setMode   = usePlayback((s) => s.setMode);
  const lens      = usePlayback((s) => s.lens);
  const toggleHoe = usePlayback((s) => s.toggleHoe);
  const toggleWanneer = usePlayback((s) => s.toggleWanneer);

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

  // Lens-pill — visually distinct from playback buttons.  Active state uses the
  // Messi-gold accent so the viewer sees which interpretive layers are on.
  const LensPill = ({ on, onClick, label, preview }:
    { on: boolean; onClick: () => void; label: string; preview?: boolean }) => (
    <button onClick={onClick}
            style={{
              background: on ? (preview ? `${C.messi}22` : `${C.messi}33`) : "transparent",
              border: `1px solid ${on ? C.messi : C.line}`,
              color: on ? C.messi : C.textDim,
              padding: "8px 16px",
              fontFamily: FONT.sans,
              fontSize: 11,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              fontWeight: 600,
              cursor: "pointer",
              transition: "color 0.2s, border-color 0.2s, background 0.2s",
              position: "relative",
            }}>
      {label}
      {preview && on && (
        <span style={{
          position: "absolute", top: -7, right: -7,
          fontSize: 8, letterSpacing: "0.1em",
          background: C.bg, border: `1px solid ${C.messi}66`,
          color: C.messi, padding: "1px 4px", borderRadius: 8,
          fontWeight: 500,
        }}>
          preview
        </span>
      )}
    </button>
  );

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
          <span style={{ width: 8 }} />
          <Btn onClick={togglePause}>
            {progress >= 1 ? "Klaar"
             : isPaused ? "▶ Hervat"
                        : "Pauzeer"}
          </Btn>
          <Btn onClick={reset}>↻ Opnieuw</Btn>
        </>
      )}

      {/* Lens-schakelaars — onafhankelijk, kunnen alle 4 combinaties hebben.
          Hoe is functioneel; Wanneer is een preview-schakelaar voor stap 6. */}
      <span style={{ width: 16 }} />
      <span style={{ color: C.textFade, fontSize: 9, letterSpacing: "0.18em",
                     textTransform: "uppercase", fontFamily: FONT.sans }}>
        lens
      </span>
      <LensPill on={lens.hoe} onClick={toggleHoe} label="Hoe" />
      <LensPill on={lens.wanneer} onClick={toggleWanneer} label="Wanneer" preview />

      {mode === "cinematic" && (
        <span style={{ color: C.textFade, fontSize: 10,
                       letterSpacing: "0.14em", textTransform: "uppercase",
                       fontFamily: FONT.sans, marginLeft: 8 }}>
          Spatie · pauze   ·   R · opnieuw
        </span>
      )}

      {mode === "scroll" && (
        <span style={{ color: C.textFade, fontSize: 10,
                       letterSpacing: "0.14em", textTransform: "uppercase",
                       fontFamily: FONT.sans, marginLeft: 8 }}>
          Scroll om door de aanval te bewegen
        </span>
      )}
    </div>
  );
}
