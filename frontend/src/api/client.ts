/**
 * @file client.ts
 * @description Type-safe API client for Steamhub backend with HttpOnly cookie credentials
 * @module frontend/api
 */

import type {
  HealthStatus,
  HeatmapResponse,
  ManualPollResponse,
  User,
  UserGameStat,
  UserStatus,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    credentials: "include", // Required for HttpOnly session and CSRF cookies
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let errorDetail = "An unexpected error occurred.";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export async function fetchCurrentUser(): Promise<User | null> {
  try {
    return await request<User>("/api/auth/me");
  } catch {
    return null;
  }
}

export async function fetchUserHeatmap(
  userId: string,
  year: number
): Promise<HeatmapResponse> {
  return request<HeatmapResponse>(`/api/users/${userId}/heatmap?year=${year}`);
}

export async function fetchUserGames(
  userId: string
): Promise<UserGameStat[]> {
  return request<UserGameStat[]>(`/api/users/${userId}/games`);
}

export async function fetchUserStatus(userId: string): Promise<UserStatus> {
  return request<UserStatus>(`/api/users/${userId}/status`);
}

export async function triggerManualPoll(
  userId: string
): Promise<ManualPollResponse> {
  return request<ManualPollResponse>(`/api/users/${userId}/poll`, {
    method: "POST",
  });
}

export async function logoutUser(): Promise<{ success: boolean }> {
  return request<{ success: boolean }>("/api/auth/logout", {
    method: "POST",
  });
}

export async function fetchHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/api/health");
}

export function getSteamLoginUrl(): string {
  return `${API_BASE_URL}/auth/steam/login`;
}
