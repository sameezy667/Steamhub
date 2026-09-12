/**
 * @file App.tsx
 * @description Root application component managing state, authentication, and contribution dashboard
 * @module frontend
 */

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "./components/Header";
import { StatusBanner } from "./components/StatusBanner";
import { Heatmap } from "./components/Heatmap";
import { YearSelector } from "./components/YearSelector";
import { GameBreakdown } from "./components/GameBreakdown";
import {
  fetchCurrentUser,
  fetchUserGames,
  fetchUserHeatmap,
  fetchUserStatus,
  logoutUser,
  triggerManualPoll,
} from "./api/client";
import type {
  HeatmapDayItem,
  User,
  UserGameStat,
  UserStatus,
} from "./types";

// Mock data generator for interactive demo preview mode
function generateDemoData() {
  const demoConnectedAt = "2026-03-15T12:00:00Z";

  const demoUser: User = {
    id: "demo-user-uuid-1234",
    steam_id64: "76561198034291845",
    persona_name: "ShadowSniper",
    avatar_url:
      "https://avatars.steamstatic.com/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg",
    profile_visibility_state: 3,
    connected_at: demoConnectedAt,
    last_polled_at: new Date(Date.now() - 15 * 60000).toISOString(),
  };

  const demoStatus: UserStatus = {
    user_id: demoUser.id,
    steam_id64: demoUser.steam_id64,
    persona_name: demoUser.persona_name,
    avatar_url: demoUser.avatar_url,
    profile_visibility_state: 3,
    connected_at: demoConnectedAt,
    last_polled_at: demoUser.last_polled_at,
    total_games_tracked: 4,
    is_polling_allowed: true,
    next_poll_allowed_at: null,
  };

  const demoGames: UserGameStat[] = [
    {
      app_id: 730,
      name: "Counter-Strike 2",
      icon_url: "cs2_demo",
      lifetime_tracked_minutes: 8420,
      last_played_date: "2026-09-11",
    },
    {
      app_id: 1245620,
      name: "ELDEN RING",
      icon_url: "elden_demo",
      lifetime_tracked_minutes: 6240,
      last_played_date: "2026-09-08",
    },
    {
      app_id: 1091500,
      name: "Cyberpunk 2077",
      icon_url: "cyberpunk_demo",
      lifetime_tracked_minutes: 4180,
      last_played_date: "2026-08-25",
    },
    {
      app_id: 570,
      name: "Dota 2",
      icon_url: "dota2_demo",
      lifetime_tracked_minutes: 3890,
      last_played_date: "2026-09-02",
    },
  ];

  // Generate simulated activity for 2026 post-connection
  const demoDays: HeatmapDayItem[] = [];
  const startDate = new Date(Date.UTC(2026, 2, 16)); // Start after March 15
  const endDate = new Date(Date.UTC(2026, 8, 12)); // Until local date

  let curr = new Date(startDate);
  while (curr <= endDate) {
    const dateStr = curr.toISOString().split("T")[0];
    const dayOfWeek = curr.getUTCDay();

    // Play more on weekends
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6 || dayOfWeek === 5;
    const playChance = isWeekend ? 0.75 : 0.45;

    if (Math.random() < playChance) {
      const minutes = isWeekend
        ? Math.floor(Math.random() * 320) + 60
        : Math.floor(Math.random() * 180) + 20;

      const randomGame =
        demoGames[Math.floor(Math.random() * demoGames.length)];

      demoDays.push({
        date: dateStr,
        total_minutes: minutes,
        top_game: {
          app_id: randomGame.app_id,
          name: randomGame.name,
          icon_url: randomGame.icon_url,
          minutes_played: Math.floor(minutes * 0.75),
        },
      });
    }

    curr.setUTCDate(curr.getUTCDate() + 1);
  }

  const totalMinutes = demoDays.reduce((acc, d) => acc + d.total_minutes, 0);

  return {
    user: demoUser,
    status: demoStatus,
    games: demoGames,
    heatmapDays: demoDays,
    totalMinutes,
  };
}

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [userStatus, setUserStatus] = useState<UserStatus | null>(null);
  const [userGames, setUserGames] = useState<UserGameStat[]>([]);
  const [heatmapDays, setHeatmapDays] = useState<HeatmapDayItem[]>([]);
  const [connectedAt, setConnectedAt] = useState<string>("2026-01-01T00:00:00Z");
  const [totalYearMinutes, setTotalYearMinutes] = useState<number>(0);
  const [selectedYear, setSelectedYear] = useState<number>(2026);
  const [isPolling, setIsPolling] = useState<boolean>(false);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true); // Default to interactive demo for instant preview
  const [notification, setNotification] = useState<string | null>(null);

  const showNotification = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  const loadUserData = useCallback(async (userId: string, year: number) => {
    try {
      const [hmRes, stRes, gmRes] = await Promise.all([
        fetchUserHeatmap(userId, year),
        fetchUserStatus(userId),
        fetchUserGames(userId),
      ]);
      setHeatmapDays(hmRes.days);
      setTotalYearMinutes(hmRes.total_year_minutes);
      setConnectedAt(hmRes.connected_at);
      setUserStatus(stRes);
      setUserGames(gmRes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load data";
      showNotification(msg);
    }
  }, []);

  // Check current session on mount
  useEffect(() => {
    const initAuth = async () => {
      const user = await fetchCurrentUser();
      if (user) {
        setCurrentUser(user);
        setIsDemoMode(false);
        await loadUserData(user.id, selectedYear);
      } else {
        // Load demo data
        const demo = generateDemoData();
        setCurrentUser(demo.user);
        setUserStatus(demo.status);
        setUserGames(demo.games);
        setHeatmapDays(demo.heatmapDays);
        setTotalYearMinutes(demo.totalMinutes);
        setConnectedAt(demo.user.connected_at);
      }
    };
    initAuth();
  }, [loadUserData, selectedYear]);

  const handleToggleDemo = () => {
    if (isDemoMode) {
      // Switch to live unauthenticated mode
      setIsDemoMode(false);
      setCurrentUser(null);
      setUserStatus(null);
      setUserGames([]);
      setHeatmapDays([]);
      setTotalYearMinutes(0);
    } else {
      // Switch to demo mode
      setIsDemoMode(true);
      const demo = generateDemoData();
      setCurrentUser(demo.user);
      setUserStatus(demo.status);
      setUserGames(demo.games);
      setHeatmapDays(demo.heatmapDays);
      setTotalYearMinutes(demo.totalMinutes);
      setConnectedAt(demo.user.connected_at);
    }
  };

  const handleManualPoll = async () => {
    if (isDemoMode) {
      setIsPolling(true);
      showNotification("Demo Mode: Simulated Steam sync complete!");
      setTimeout(() => {
        setIsPolling(false);
      }, 1200);
      return;
    }

    if (!currentUser) return;
    setIsPolling(true);
    try {
      const res = await triggerManualPoll(currentUser.id);
      showNotification(res.message);
      await loadUserData(currentUser.id, selectedYear);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Poll request failed";
      showNotification(msg);
    } finally {
      setIsPolling(false);
    }
  };

  const handleLogout = async () => {
    if (isDemoMode) {
      handleToggleDemo();
      return;
    }
    await logoutUser();
    setCurrentUser(null);
    setUserStatus(null);
    setUserGames([]);
    setHeatmapDays([]);
    showNotification("Logged out successfully.");
  };

  const handleSelectYear = async (year: number) => {
    setSelectedYear(year);
    if (!isDemoMode && currentUser) {
      await loadUserData(currentUser.id, year);
    }
  };

  const activeDaysCount = heatmapDays.filter((d) => d.total_minutes > 0).length;

  return (
    <div className="app-container">
      <Header
        user={currentUser}
        status={userStatus}
        onLogout={handleLogout}
        onManualPoll={handleManualPoll}
        isPolling={isPolling}
        isDemoMode={isDemoMode}
        onToggleDemo={handleToggleDemo}
      />

      <main className="main-content">
        {notification && (
          <div
            style={{
              background: "rgba(102, 192, 244, 0.15)",
              border: "1px solid var(--steam-cyan)",
              color: "#ffffff",
              padding: "12px 18px",
              borderRadius: "8px",
              fontSize: "13px",
              fontWeight: 600,
            }}
          >
            {notification}
          </div>
        )}

        {/* Profile Privacy Warning Banner */}
        <StatusBanner
          visibilityState={userStatus?.profile_visibility_state}
        />

        {/* Year Filter & Annual Stats */}
        <YearSelector
          selectedYear={selectedYear}
          availableYears={[2026, 2025, 2024]}
          totalYearMinutes={totalYearMinutes}
          activeDaysCount={activeDaysCount}
          onSelectYear={handleSelectYear}
        />

        {/* 3-State Contribution Heatmap Grid */}
        <Heatmap
          year={selectedYear}
          connectedAt={connectedAt}
          days={heatmapDays}
        />

        {/* Lifetime Tracked Games Breakdown */}
        <GameBreakdown games={userGames} />
      </main>
    </div>
  );
};

export default App;
