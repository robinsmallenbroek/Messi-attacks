// =============================================================================
//  AttackScene — root SVG canvas, layer-aware.
//
//  THREE LAYERS (see frontend/src/LAYERS.md for full table):
//    BASIS      — always visible:  pitch, ball, players, timeline, leader-line,
//                                  freeze-frame, metric strip
//    HOE        — visible if lens.hoe:  pressure ring, knikpunten, percentile
//                                       contexts at dribble and shot
//    WANNEER    — visible if lens.wanneer:  (stap 6; placeholder only here)
//
//  Conditional rendering convention:
//    Components that belong to a lens read `usePlayback(s => s.lens.X)` and
//    return null when off.  Basis components never read `lens.*`.
// =============================================================================
import type { AttackData } from "../types";
import Pitch, { pitchBallPosition } from "./Pitch";
import Timeline, { timelinePlayheadX } from "./Timeline";
import { C, FONT } from "../lib/theme";
import { usePlayback } from "../store";
import { progressToRealTime, getPhaseInfo } from "../lib/playback";

interface Props {
  data: AttackData;
}

export default function AttackScene({ data }: Props) {
  const progress  = usePlayback((s) => s.progress);
  const realTime  = progressToRealTime(progress);
  const { phase, phaseProgress } = getPhaseInfo(progress);
  const wanneerOn = usePlayback((s) => s.lens.wanneer);

  const W = 1280;
  const H = 860;

  const pad     = 60;
  const pitchY  = 10;
  const pitchH  = 530;
  const pitchX  = pad;
  const pitchW  = W - pad * 2;

  const tlY = 690;
  const tlH = 100;
  const tlX = pad;
  const tlW = pitchW;

  // Leader line: from timeline playhead UP to ball position on pitch.
  // The bridging diagonal is the visual contract: at this time-X the ball
  // is at this space-XY.  Keep it thin and warm so it reads as a link, not
  // a divider.  Fades during freeze-reveal so the climax has the stage.
  const ball = pitchBallPosition(data, pitchX, pitchY, pitchW, pitchH, realTime);
  const playX = timelinePlayheadX(tlX, tlW, data.meta.duration_seconds, realTime);
  const inShotHold = phase.label === "shot-hold";
  const leaderOpacity = inShotHold ? Math.max(0, 0.55 - phaseProgress * 0.55) : 0.55;

  return (
    <svg viewBox={`0 0 ${W} ${H}`}
         style={{ width: "100%", height: "auto", background: "transparent" }}>

      <Pitch  data={data} x={pitchX} y={pitchY} width={pitchW} height={pitchH}
              realTime={realTime}
              phaseLabel={phase.label ?? ""}
              phaseProgress={phaseProgress} />

      {/* Leader line — the join between time and space.
          Two segments: (a) vertical from playhead up to pitch baseline,
          (b) diagonal from pitch baseline to current ball position. */}
      {ball && leaderOpacity > 0.02 && (
        <g opacity={leaderOpacity}>
          <line x1={playX} y1={tlY - 4} x2={playX} y2={pitchY + pitchH + 18}
                stroke={C.shot} strokeWidth={0.8} strokeDasharray="3 3" />
          <line x1={playX} y1={pitchY + pitchH + 18}
                x2={ball.x} y2={ball.y}
                stroke={C.shot} strokeWidth={0.8} strokeDasharray="3 3" />
        </g>
      )}

      <text x={pitchX} y={pitchY + pitchH + 38}
            fill={C.textDim} fontSize={10} letterSpacing="0.15em"
            fontFamily={FONT.sans}>
        TIJD →
      </text>

      {/* Phase indicator — small, right-aligned, for the curious */}
      <text x={pitchX + pitchW} y={pitchY + pitchH + 38}
            fill={C.textFade} fontSize={10} letterSpacing="0.1em"
            textAnchor="end" fontFamily={FONT.sans}>
        {phase.label?.replace(/-/g, " ").toUpperCase()}
      </text>

      {/* Wanneer-laag preview placeholder — toont alleen dat de schakelaar
          functioneel is; echte content komt in stap 6. */}
      {wanneerOn && (
        <g>
          <rect x={pitchX + pitchW - 220} y={pitchY + 8} width={212} height={22}
                fill={C.bg} stroke={C.line} strokeWidth={0.6} opacity={0.85} />
          <text x={pitchX + pitchW - 12} y={pitchY + 22}
                fill={C.textDim} fontSize={10} letterSpacing="0.16em"
                textAnchor="end" fontFamily={FONT.sans}
                fontStyle="italic">
            Wanneer-laag · komt in stap 6
          </text>
        </g>
      )}

      <Timeline data={data} x={tlX} y={tlY} width={tlW} height={tlH}
                realTime={realTime} />
    </svg>
  );
}
