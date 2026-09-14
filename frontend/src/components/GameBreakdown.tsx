/**
 * @file GameBreakdown.tsx
 * @description Tracked games breakdown cards with lifetime hours, last active timestamps, and gaming iconography
 * @module frontend/components
 */

import React from "react";
import { Calendar, Clock, Gamepad2 } from "lucide-react";
import type { UserGameStat } from "../types";
import en from "../locales/en.json";

interface GameBreakdownProps {
  games: UserGameStat[];
}

export const GameBreakdown: React.FC<GameBreakdownProps> = ({ games }) => {
  const formatPlaytimeHours = (mins: number) => {
    const hours = (mins / 60).toFixed(1);
    return `${hours} hrs`;
  };

  const formatTotalTime = (mins: number) => {
    const hours = Math.floor(mins / 60);
    const m = mins % 60;
    return `${hours}h ${m}m`;
  };

  return (
    <div className="games-section">
      <div className="section-header">
        <div className="section-title-row">
          <div className="section-icon-badge">
            <Gamepad2 size={20} className="text-steam-cyan" />
          </div>
          <div>
            <h2 className="section-title">{en.games.title}</h2>
            <p className="section-subtitle">{en.games.subheading}</p>
          </div>
        </div>
      </div>

      {games.length === 0 ? (
        <div className="empty-games-card">
          <div className="empty-games-icon-wrap">
            <Gamepad2 size={36} className="text-slate-500" />
          </div>
          <h3 className="empty-games-title">No game activity recorded yet</h3>
          <p className="empty-games-desc">{en.games.no_games}</p>
        </div>
      ) : (
        <div className="games-grid">
          {games.map((game, idx) => (
            <div key={game.app_id} className="game-card" style={{ animationDelay: `${idx * 60}ms` }}>
              <div className="game-card-top-glow" />
              <div className="game-card-left">
                {game.icon_url ? (
                  <img
                    src={`https://media.steampowered.com/steamcommunity/public/images/apps/${game.app_id}/${game.icon_url}.jpg`}
                    alt={game.name}
                    className="game-icon"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = "none";
                    }}
                  />
                ) : (
                  <div className="game-icon-fallback">
                    <Gamepad2 size={22} className="text-steam-cyan" />
                  </div>
                )}
                <div className="game-info">
                  <h4 className="game-name" title={game.name}>
                    {game.name}
                  </h4>
                  <span className="game-appid">App ID: {game.app_id}</span>
                </div>
              </div>

              <div className="game-card-right">
                <div className="game-stat">
                  <span className="stat-label">{en.games.lifetime_hours}</span>
                  <div className="stat-value hours-glow">
                    <Clock size={14} className="text-steam-green" />
                    <span>{formatPlaytimeHours(game.lifetime_tracked_minutes)}</span>
                  </div>
                  <span className="stat-sub">{formatTotalTime(game.lifetime_tracked_minutes)}</span>
                </div>

                {game.last_played_date && (
                  <div className="game-stat last-played">
                    <span className="stat-label">{en.games.last_played}</span>
                    <div className="stat-value text-slate-400">
                      <Calendar size={13} />
                      <span>{game.last_played_date}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
