/**
 * @file GameBreakdown.tsx
 * @description Tracked games breakdown cards with lifetime hours and last active timestamps
 * @module frontend/components
 */

import React from "react";
import { Calendar, Clock, Gamepad2, Sparkles } from "lucide-react";
import type { UserGameStat } from "../types";
import en from "../locales/en.json";

interface GameBreakdownProps {
  games: UserGameStat[];
}

export const GameBreakdown: React.FC<GameBreakdownProps> = ({ games }) => {
  const formatPlaytime = (mins: number) => {
    const hours = (mins / 60).toFixed(1);
    return `${hours} hrs`;
  };

  return (
    <div className="games-section">
      <div className="section-header">
        <div className="section-title-row">
          <Gamepad2 size={22} className="text-steam-cyan" />
          <h2 className="section-title">{en.games.title}</h2>
        </div>
        <p className="section-subtitle">{en.games.subheading}</p>
      </div>

      {games.length === 0 ? (
        <div className="empty-games-card">
          <Sparkles size={32} className="text-slate-500" />
          <p>{en.games.no_games}</p>
        </div>
      ) : (
        <div className="games-grid">
          {games.map((game) => (
            <div key={game.app_id} className="game-card">
              <div className="game-card-left">
                {game.icon_url ? (
                  <img
                    src={`https://media.steampowered.com/steamcommunity/public/images/apps/${game.app_id}/${game.icon_url}.jpg`}
                    alt={game.name}
                    className="game-icon"
                    onError={(e) => {
                      // Fallback if icon fails to load
                      (e.target as HTMLElement).style.display = "none";
                    }}
                  />
                ) : (
                  <div className="game-icon-fallback">
                    <Gamepad2 size={20} className="text-steam-cyan" />
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
                  <div className="stat-value text-steam-green">
                    <Clock size={14} />
                    <span>{formatPlaytime(game.lifetime_tracked_minutes)}</span>
                  </div>
                </div>

                {game.last_played_date && (
                  <div className="game-stat">
                    <span className="stat-label">{en.games.last_played}</span>
                    <div className="stat-value text-slate-400">
                      <Calendar size={14} />
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
