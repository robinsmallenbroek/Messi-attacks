import { useRef } from "react";
import attackData from "./data/zaragoza_2012.json";
import type { AttackData } from "./types";
import AttackScene from "./components/AttackScene";
import MetricStrip from "./components/MetricStrip";
import Controls from "./components/Controls";
import PhaseWhisper from "./components/PhaseWhisper";
import { IntroOverlay, OutroPanel } from "./components/Overlays";
import { usePlaybackEngine } from "./hooks/usePlaybackEngine";
import { useScrollProgress } from "./hooks/useScrollProgress";
import { usePlayback } from "./store";
import { C, FONT } from "./lib/theme";

const data = attackData as AttackData;

const SCROLL_HEIGHT_VH = 300;

function PageHeader() {
  const m = data.meta;
  return (
    <header style={{ marginBottom: 22, paddingLeft: 60, paddingRight: 60, maxWidth: 1280 }}>
      <div style={{ color: C.textDim, fontSize: 11, letterSpacing: "0.2em",
                    textTransform: "uppercase", marginBottom: 8 }}>
        Lens 02 · Individuele virtuositeit
      </div>
      <h1 style={{ fontFamily: FONT.serif, fontWeight: 300, fontSize: 40,
                   letterSpacing: "-0.015em", margin: 0, lineHeight: 1.08,
                   color: C.text }}>
        <span style={{ color: C.messi, fontWeight: 400 }}>Messi</span> tegen Real Zaragoza
      </h1>
      <div style={{ color: C.textDim, fontSize: 13, marginTop: 8 }}>
        {m.match_date} · {m.home_team} {m.score} {m.away_team} · La Liga {m.season}
        {" · "}<span style={{ color: C.text }}>minuut {m.minute}</span>
      </div>
    </header>
  );
}

function StageContents() {
  return (
    <>
      <PageHeader />
      <AttackScene data={data} />
      <PhaseWhisper />
      <MetricStrip data={data} />
      <Controls />
    </>
  );
}

function CinematicLayout() {
  return (
    <div style={{
      minHeight: "100vh",
      background: C.bg,
      color: C.text,
      fontFamily: FONT.sans,
      padding: "40px 0 64px",
    }}>
      <StageContents />
      <OutroPanel data={data} />
      <IntroOverlay data={data} />

      <footer style={{ marginTop: 36, paddingLeft: 60,
                       color: C.textFade, fontSize: 10,
                       letterSpacing: "0.16em", textTransform: "uppercase" }}>
        Data · StatsBomb Open Data
      </footer>
    </div>
  );
}

function ScrollLayout() {
  const scrollRef = useRef<HTMLDivElement>(null);
  useScrollProgress(true, scrollRef);
  const progress = usePlayback((s) => s.progress);

  return (
    <div style={{
      background: C.bg, color: C.text, fontFamily: FONT.sans,
    }}>
      <div ref={scrollRef}
           style={{ height: `${SCROLL_HEIGHT_VH}vh`, position: "relative" }}>
        <div style={{
          position: "sticky", top: 0,
          height: "100vh", overflow: "hidden",
          padding: "32px 0",
          display: "flex", flexDirection: "column",
        }}>
          <StageContents />

          <div style={{
            position: "absolute", right: 18, top: "20%", bottom: "20%",
            width: 2, background: C.lineMuted, opacity: 0.4, borderRadius: 1,
          }}>
            <div style={{
              position: "absolute", left: -3, width: 8, height: 8,
              top: `${progress * 100}%`,
              background: C.shot, borderRadius: 4,
              transform: "translateY(-50%)",
            }} />
          </div>

          <div style={{
            position: "absolute", right: 12, bottom: 24,
            color: C.textFade, fontSize: 9, letterSpacing: "0.2em",
            textTransform: "uppercase", writingMode: "vertical-rl",
            transform: "rotate(180deg)",
          }}>
            Scroll · {Math.round(progress * 100)} %
          </div>
        </div>
      </div>

      <footer style={{ paddingLeft: 60, paddingBottom: 48,
                       color: C.textFade, fontSize: 10,
                       letterSpacing: "0.16em", textTransform: "uppercase" }}>
        Data · StatsBomb Open Data
      </footer>
    </div>
  );
}

export default function App() {
  usePlaybackEngine();
  const mode = usePlayback((s) => s.mode);
  return mode === "scroll" ? <ScrollLayout /> : <CinematicLayout />;
}
