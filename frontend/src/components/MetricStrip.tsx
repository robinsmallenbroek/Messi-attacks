import type { AttackData } from "../types";
import { usePlayback } from "../store";
import { progressToRealTime } from "../lib/playback";
import { C, FONT } from "../lib/theme";

interface Props { data: AttackData }

/** Inline metrics that update with the playback.  Style: minimal, no cards,
 *  small typography, monospace digits so the numbers don't jitter as they tick.
 */
export default function MetricStrip({ data }: Props) {
  const progress = usePlayback((s) => s.progress);
  const realTime = progressToRealTime(progress);

  // Compute current values by walking events up to realTime
  let touches = 0;
  let beaten  = 0;
  let speed: number | null = null;
  for (const e of data.events) {
    if (e.t_seconds > realTime) break;
    if (e.player_short === "Messi") touches = e.cumulative_messi_touches;
    beaten = e.opponents_beaten_so_far;
    if (e.ball_speed_mps !== null) speed = e.ball_speed_mps;
  }

  const Item = ({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 110 }}>
      <span style={{ color: C.textDim, fontSize: 10, letterSpacing: "0.14em",
                     textTransform: "uppercase" }}>{label}</span>
      <span style={{ color: accent ? C.messi : C.text, fontSize: 22,
                     fontFamily: FONT.serif, fontWeight: 400, lineHeight: 1,
                     fontVariantNumeric: "tabular-nums" }}>{value}</span>
    </div>
  );

  return (
    <div style={{ display: "flex", gap: 36, alignItems: "flex-end",
                  marginTop: 28, paddingLeft: 60, paddingRight: 60,
                  fontFamily: FONT.sans }}>
      <Item label="Tijd"      value={`${realTime.toFixed(2)}s`} />
      <Item label="Touches"   value={`${touches}`} accent={touches > 0} />
      <Item label="Gepasseerd" value={`${beaten}`} />
      <Item label="Bal-snelheid" value={speed !== null ? `${speed.toFixed(1)} m/s` : "—"} />
    </div>
  );
}
