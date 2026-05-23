import { useEffect, useRef, useState } from "react";
import { usePlayback } from "../store";
import { getPhaseInfo } from "../lib/playback";
import { C, FONT } from "../lib/theme";

/** A small line of text that fades in briefly when a new phase starts.
 *  Used as ambient narrative pacing — the viewer can read it or ignore it.
 *  Only active in cinematic mode. */
const PHASE_TEXT: Record<string, string> = {
  "intro-hold":              "",
  "alexis-carry":            "Alexis intercept · 43m carry naar voren",
  "pass-arrival-hold":       "Pass arriveert bij Messi",
  "messi-receives":          "Messi ontvangt onder druk",
  "messi-carries-to-dribble":"Messi draagt door verdedigers",
  "dribble-beat-hold":       "Barrios gepasseerd",
  "shot-approach":           "Pintér drukt · schot inkomend",
  "shot-hold":               "Schot · ruimte rond Messi onthuld",
};

export default function PhaseWhisper() {
  const mode      = usePlayback((s) => s.mode);
  const progress  = usePlayback((s) => s.progress);
  const { phase } = getPhaseInfo(progress);

  const [shownLabel, setShownLabel] = useState("");
  const [opacity, setOpacity] = useState(0);
  const lastLabel = useRef("");
  const fadeOutTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (mode !== "cinematic") { setOpacity(0); return; }
    const label = phase.label ?? "";
    if (label === lastLabel.current) return;
    lastLabel.current = label;
    const text = PHASE_TEXT[label] ?? "";
    if (!text) { setOpacity(0); return; }
    setShownLabel(text);
    setOpacity(1);
    if (fadeOutTimer.current) window.clearTimeout(fadeOutTimer.current);
    fadeOutTimer.current = window.setTimeout(() => setOpacity(0), 1800);
    return () => {
      if (fadeOutTimer.current) window.clearTimeout(fadeOutTimer.current);
    };
  }, [phase.label, mode]);

  if (mode !== "cinematic") return null;

  return (
    <div style={{
      paddingLeft: 60, paddingRight: 60, marginTop: 14,
      maxWidth: 900,
      height: 22,
      fontFamily: FONT.sans,
    }}>
      <span style={{
        color: C.textDim, fontSize: 12, letterSpacing: "0.16em",
        textTransform: "uppercase", fontStyle: "italic",
        opacity, transition: "opacity 0.6s ease",
      }}>
        {shownLabel}
      </span>
    </div>
  );
}
