// Types matching the export from pipeline/export_attack.py

export type Location = [number, number];

export interface AttackMeta {
  match_id: number;
  possession_id: number;
  match_date: string;
  competition: string;
  season: string;
  home_team: string;
  away_team: string;
  score: string;
  minute: number;
  duration_seconds: number;
  n_events: number;
  n_dribbles: number;
  n_carries: number;
  n_passes: number;
  messi_touches_total: number;
  opponents_beaten_total: number;
  shot_xg: number | null;
  shot_outcome: string | null;
  scorer: string | null;
  pitch: { length: number; width: number };
}

export interface BarcaPlayer {
  id: number;
  name: string;
  short_name: string;
  position: string | null;
}

export interface OpponentBeaten {
  id: number;
  name: string;
  short_name: string;
  location: Location | null;
  team: string;
}

export interface PassInfo {
  id: number;
  name: string;
  short_name: string;
}

export interface ShotInfo {
  xg: number | null;
  outcome: string | null;
  end_location: Location | null;
  end_height: number | null;
  technique: string | null;
  body_part: string | null;
}

export interface DribbleInfo {
  outcome: string | null;
}

export interface CarryInfo {
  end_location: Location | null;
}

export interface AttackEvent {
  id: string;
  index: number;
  period: number;
  timestamp: string;
  minute: number;
  second: number;
  t_seconds: number;
  type: string;
  player_id: number | null;
  player_name: string | null;
  player_short: string;
  team: string | null;
  location: Location | null;
  duration: number | null;
  under_pressure: boolean;
  inter_event_seconds: number;
  ball_speed_mps: number | null;
  cumulative_messi_touches: number;
  opponents_beaten_so_far: number;
  pass: PassInfo | null;
  dribble: DribbleInfo | null;
  opponent_beaten: OpponentBeaten | null;
  carry: CarryInfo | null;
  shot: ShotInfo | null;
}

export interface FreezeFramePlayer {
  location: Location;
  player_id: number | null;
  name: string | null;
  short_name: string;
  position: string | null;
  teammate: boolean;
  actor: boolean;
}

export interface AttackData {
  meta: AttackMeta;
  barca_players: BarcaPlayer[];
  events: AttackEvent[];
  freeze_frame: FreezeFramePlayer[];
}

export type PlaybackMode = "cinematic" | "scroll";
