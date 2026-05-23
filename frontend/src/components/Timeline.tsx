import type { AttackData, AttackEvent } from "../types";
import { C, FONT } from "../lib/theme";

interface Props {
  data: AttackData;
  x: number;
  y: number;
  width: number;
  height: number;
  realTime: number;
}

function eventColor(e: AttackEvent): string {
  if (e.player_short === "Messi") return C.messi;
  if (e.team === "Barcelona") return C.barca;
  return C.opp;
}

function smooth(t: number): number {
  const c = Math.max(0, Math.min(1, t));
  return c * c * (3 - 2 * c);
}

function EventGlyph({ type, x, y, color, scale = 1 }:
  { type: string; x: number; y: number; color: string; scale?: number }) {
  switch (type) {
    case "Pass":
      return <line x1={x - 5*scale} y1={y} x2={x + 5*scale} y2={y} stroke={color} strokeWidth={1.5} />;
    case "Carry":
      return (
        <line x1={x - 5*scale} y1={y} x2={x + 5*scale} y2={y} stroke={color} strokeWidth={1.5}
              strokeDasharray="2 1.5" />
      );
    case "Dribble":
      return <circle cx={x} cy={y} r={3.5*scale} fill="none" stroke={color} strokeWidth={1.5} />;
    case "Shot":
      return <circle cx={x} cy={y} r={4.5*scale} fill={color} />;
    case "Ball Receipt*":
      return <circle cx={x} cy={y} r={2*scale} fill={color} />;
    case "Pressure":
    case "Dribbled Past":
      return (
        <path d={`M ${x - 3.5*scale} ${y - 3.5*scale} L ${x + 3.5*scale} ${y + 3.5*scale} M ${x - 3.5*scale} ${y + 3.5*scale} L ${x + 3.5*scale} ${y - 3.5*scale}`}
              stroke={color} strokeWidth={1.2} />
      );
    case "Interception":
      return <polygon points={`${x},${y - 4*scale} ${x + 3.5*scale},${y + 3*scale} ${x - 3.5*scale},${y + 3*scale}`} fill={color} />;
    default:
      return <circle cx={x} cy={y} r={2*scale} fill={color} opacity={0.6} />;
  }
}

export default function Timeline({ data, x, y, width, height, realTime }: Props) {
  const events = data.events;
  const total = data.meta.duration_seconds;
  const xFor = (t: number) => x + (t / total) * width;
  const axisY = y + height / 2;

  const pauseBands = events
    .map((e, i) => ({ e, i }))
    .filter(({ e, i }) => i > 0 && e.inter_event_seconds >= 2.0)
    .map(({ e, i }) => ({
      from: events[i - 1].t_seconds,
      to:   e.t_seconds,
      prevPlayer: events[i - 1].player_short,
    }));

  // Playhead position
  const playheadX = xFor(realTime);

  // Are we currently *inside* a pause band?  Used to subtly intensify it.
  const inPause = pauseBands.some(p => realTime >= p.from && realTime <= p.to);

  return (
    <g fontFamily={FONT.sans}>
      <line x1={x} y1={axisY} x2={x + width} y2={axisY}
            stroke={C.lineMuted} strokeWidth={1} />

      <text x={x} y={axisY + 30} fill={C.textDim} fontSize={11}>0.0 s</text>
      <text x={x + width} y={axisY + 30} fill={C.textDim} fontSize={11}
            textAnchor="end">{total.toFixed(2)} s</text>

      {/* Pause bands */}
      {pauseBands.map((p, idx) => {
        const isActive = realTime >= p.from && realTime <= p.to;
        return (
          <g key={idx}>
            <rect x={xFor(p.from)} y={axisY - 20} width={xFor(p.to) - xFor(p.from)} height={40}
                  fill={C.pause} opacity={isActive ? 0.95 : 0.6} />
            <text x={(xFor(p.from) + xFor(p.to)) / 2} y={axisY + 48}
                  fill={isActive ? C.textDim : C.textFade}
                  fontSize={10} textAnchor="middle" fontStyle="italic">
              {(p.to - p.from).toFixed(2)} s — {p.prevPlayer} carries
            </text>
          </g>
        );
      })}

      {/* Events — they fade in when the playhead reaches them */}
      {events.map((e, i) => {
        const ex = xFor(e.t_seconds);
        const color = eventColor(e);
        const sameTimeOffset = events
          .slice(0, i)
          .filter((p) => Math.abs(p.t_seconds - e.t_seconds) < 0.01).length;
        const labelY = y + 14 + sameTimeOffset * 14;
        const typeY  = axisY + 16 + sameTimeOffset * 11;

        const fade = smooth((realTime - e.t_seconds + 0.05) / 0.25);
        if (fade <= 0) return null;

        // Slight "pop" at the moment the event hits the playhead
        const distFromPlayhead = Math.abs(realTime - e.t_seconds);
        const popScale = distFromPlayhead < 0.4 ? 1 + (1 - distFromPlayhead / 0.4) * 0.4 : 1;

        return (
          <g key={e.id} opacity={fade}>
            <line x1={ex} y1={axisY - 8} x2={ex} y2={labelY + 4}
                  stroke={C.lineMuted} strokeWidth={0.5} />
            <text x={ex} y={labelY} fill={color} fontSize={12}
                  textAnchor="middle" fontWeight={e.player_short === "Messi" ? 600 : 400}>
              {e.player_short}
            </text>
            <EventGlyph type={e.type} x={ex} y={axisY} color={color} scale={popScale} />
            <text x={ex} y={typeY} fill={C.textDim} fontSize={9}
                  textAnchor="middle">
              {e.type === "Ball Receipt*" ? "Receipt" : e.type}
            </text>
          </g>
        );
      })}

      {/* Playhead — vertical line indicating current attack-time */}
      <line x1={playheadX} y1={y} x2={playheadX} y2={y + height}
            stroke={inPause ? C.textDim : C.shot}
            strokeWidth={inPause ? 1.0 : 1.4}
            opacity={inPause ? 0.55 : 0.85} />
      <circle cx={playheadX} cy={axisY} r={3.5} fill={C.shot} opacity={0.9} />
    </g>
  );
}

/** Export playhead x position for the leader line. */
export function timelinePlayheadX(x: number, width: number,
                                   totalDuration: number, realTime: number): number {
  return x + (realTime / totalDuration) * width;
}
