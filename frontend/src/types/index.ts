/**
 * @file index.ts
 * @description TypeScript interfaces for Steamhub API data models and UI state
 * @module frontend/types
 */

export interface User {
  id: string;
  steam_id64: string;
  persona_name: string;
  avatar_url: string;
  profile_visibility_state: number | null;
  connected_at: string;
  last_polled_at: string | null;
}

export interface TopGameInfo {
  app_id: number;
  name: string;
  icon_url: string;
  minutes_played: number;
}

export interface HeatmapDayItem {
  date: string; // YYYY-MM-DD
  total_minutes: number;
  top_game: TopGameInfo | null;
}

export interface HeatmapResponse {
  user_id: string;
  year: number;
  connected_at: string;
  total_year_minutes: number;
  days: HeatmapDayItem[];
}

export interface UserGameStat {
  app_id: number;
  name: string;
  icon_url: string;
  lifetime_tracked_minutes: number;
  last_played_date: string | null;
}

export interface UserStatus {
  user_id: string;
  steam_id64: string;
  persona_name: string;
  avatar_url: string;
  profile_visibility_state: number | null;
  connected_at: string;
  last_polled_at: string | null;
  total_games_tracked: number;
  is_polling_allowed: boolean;
  next_poll_allowed_at: string | null;
}

export interface ManualPollResponse {
  success: boolean;
  message: string;
  polled_at: string;
  games_observed: number;
  total_deltas_recorded: number;
}

export interface HealthStatus {
  status: string;
  environment: string;
  database_connected: boolean;
  steam_api_quota_daily: number;
  max_supported_users: number;
  registered_users_count: number;
  quota_headroom_percent: number;
}
