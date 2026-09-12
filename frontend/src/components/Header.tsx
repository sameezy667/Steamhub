/**
 * @file Header.tsx
 * @description Application top navigation bar with user profile, Steam sync button, and auth controls
 * @module frontend/components
 */

import React, { useEffect, useState } from "react";
import {
  Activity,
  Flame,
  Globe,
  Lock,
  LogOut,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import type { User, UserStatus } from "../types";
import { getSteamLoginUrl } from "../api/client";
import en from "../locales/en.json";

interface HeaderProps {
  user: User | null;
  status: UserStatus | null;
  onLogout: () => void;
  onManualPoll: () => Promise<void>;
  isPolling: boolean;
  isDemoMode: boolean;
  onToggleDemo: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  status,
  onLogout,
  onManualPoll,
  isPolling,
  isDemoMode,
  onToggleDemo,
}) => {
  const [countdown, setCountdown] = useState<number>(0);

  useEffect(() => {
    if (!status?.next_poll_allowed_at) {
      setCountdown(0);
      return;
    }

    const interval = setInterval(() => {
      const target = new Date(status.next_poll_allowed_at!).getTime();
      const now = new Date().getTime();
      const diffSeconds = Math.max(0, Math.floor((target - now) / 1000));
      setCountdown(diffSeconds);
    }, 1000);

    return () => clearInterval(interval);
  }, [status?.next_poll_allowed_at]);

  const formatCountdown = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  const isPollDisabled = isPolling || (countdown > 0 && !isDemoMode);

  return (
    <header className="header-container">
      <div className="header-content">
        {/* Brand & Title */}
        <div className="brand-section">
          <div className="brand-logo">
            <Flame className="logo-icon text-steam-cyan" size={28} />
          </div>
          <div>
            <div className="brand-title-row">
              <h1 className="brand-title">{en.app.title}</h1>
              <span className="badge-pulse">{en.app.badge}</span>
              {isDemoMode && <span className="badge-demo">Demo Mode</span>}
            </div>
            <p className="brand-subtitle">{en.app.subtitle}</p>
          </div>
        </div>

        {/* User Controls & Profile */}
        <div className="header-actions">
          {user ? (
            <div className="user-profile-bar">
              <div className="user-info">
                <img
                  src={user.avatar_url || "https://avatars.steamstatic.com/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg"}
                  alt={user.persona_name}
                  className="user-avatar"
                />
                <div className="user-details">
                  <div className="user-name-row">
                    <span className="user-name">{user.persona_name || "Steam Player"}</span>
                    {user.profile_visibility_state === 3 ? (
                      <span className="visibility-badge public" title="Public Profile">
                        <Globe size={12} />
                        Public
                      </span>
                    ) : (
                      <span className="visibility-badge private" title="Private Profile">
                        <Lock size={12} />
                        Private
                      </span>
                    )}
                  </div>
                  <span className="steam-id">{user.steam_id64}</span>
                </div>
              </div>

              {/* Sync Poll Button */}
              <button
                id="manual-poll-btn"
                onClick={onManualPoll}
                disabled={isPollDisabled}
                className={`btn-sync ${isPolling ? "polling" : ""}`}
                title={countdown > 0 ? `Cooldown active (${formatCountdown(countdown)})` : "Sync playtime from Steam"}
              >
                <RefreshCw size={16} className={isPolling ? "spin" : ""} />
                <span>
                  {isPolling
                    ? en.status.polling_now
                    : countdown > 0
                    ? `${en.status.cooldown_active} (${formatCountdown(countdown)})`
                    : en.status.poll_button}
                </span>
              </button>

              {/* Logout Button */}
              <button
                id="logout-btn"
                onClick={onLogout}
                className="btn-secondary"
                title={en.auth.logout}
              >
                <LogOut size={16} />
              </button>
            </div>
          ) : (
            <div className="auth-buttons">
              <button
                id="demo-toggle-btn"
                onClick={onToggleDemo}
                className="btn-demo"
              >
                <Sparkles size={16} />
                <span>{isDemoMode ? "Live Mode" : "Try Interactive Demo"}</span>
              </button>

              <a
                id="steam-login-btn"
                href={getSteamLoginUrl()}
                className="btn-steam-login"
              >
                <Activity size={18} />
                <span>{en.auth.login}</span>
              </a>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
