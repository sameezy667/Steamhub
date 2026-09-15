/**
 * @file Heatmap.tsx
 * @description 52-week contribution heatmap rendering 3 distinct states with larger tiles, rich tooltips, and live HUD inspection
 * @module frontend/components
 */

import React, { useMemo, useState } from "react";
import { Clock, Gamepad2, Info, Sparkles, Swords, Zap } from "lucide-react";
import type { HeatmapDayItem, TopGameInfo } from "../types";
import en from "../locales/en.json";

interface HeatmapProps {
  year: number;
  connectedAt: string;
  days: HeatmapDayItem[];
}

interface CellData {
  dateStr: string;
  dateObj: Date;
  dayOfWeek: number; // 0 = Sun, 1 = Mon ...
  weekIndex: number;
  totalMinutes: number;
  topGame: TopGameInfo | null;
  state: "untracked" | "zero" | "tier1" | "tier2" | "tier3" | "tier4";
}

interface HoverData {
  dateStr: string;
  formattedDate: string;
  totalMinutes: number;
  topGame: TopGameInfo | null;
  state: string;
}

interface TooltipState extends HoverData {
  visible: boolean;
  x: number;
  y: number;
}

export const Heatmap: React.FC<HeatmapProps> = ({
  year,
  connectedAt,
  days,
}) => {
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    dateStr: "",
    formattedDate: "",
    totalMinutes: 0,
    topGame: null,
    state: "zero",
  });

  const [activeHover, setActiveHover] = useState<HoverData | null>(null);

  // Index days by YYYY-MM-DD
  const daysMap = useMemo(() => {
    const map = new Map<string, HeatmapDayItem>();
    for (const d of days) {
      map.set(d.date, d);
    }
    return map;
  }, [days]);

  // Normalized connection date (YYYY-MM-DD)
  const connectionDateStr = useMemo(() => {
    if (!connectedAt) return "9999-12-31";
    return connectedAt.split("T")[0];
  }, [connectedAt]);

  // Build 53-week grid for the year
  const { gridWeeks, monthLabels } = useMemo(() => {
    const startDate = new Date(Date.UTC(year, 0, 1));
    const endDate = new Date(Date.UTC(year, 11, 31));

    let currentWeekIndex = 0;
    const weeks: CellData[][] = [];
    const months: { label: string; weekIndex: number }[] = [];
    let lastMonth = -1;

    const currentDate = new Date(startDate);

    while (currentDate <= endDate) {
      const month = currentDate.getUTCMonth();
      const dayOfWeek = currentDate.getUTCDay();
      const dateStr = currentDate.toISOString().split("T")[0];

      if (month !== lastMonth && dayOfWeek <= 3) {
        months.push({
          label: en.heatmap.months[month],
          weekIndex: currentWeekIndex,
        });
        lastMonth = month;
      }

      const dayData = daysMap.get(dateStr);
      const totalMins = dayData ? dayData.total_minutes : 0;
      const topGame = dayData?.top_game || null;

      // Determine 3-state classification
      let cellState: CellData["state"] = "zero";
      if (dateStr < connectionDateStr) {
        cellState = "untracked";
      } else if (totalMins === 0) {
        cellState = "zero";
      } else if (totalMins < 30) {
        cellState = "tier1";
      } else if (totalMins < 120) {
        cellState = "tier2";
      } else if (totalMins < 300) {
        cellState = "tier3";
      } else {
        cellState = "tier4";
      }

      if (!weeks[currentWeekIndex]) {
        weeks[currentWeekIndex] = [];
      }

      weeks[currentWeekIndex].push({
        dateStr,
        dateObj: new Date(currentDate),
        dayOfWeek,
        weekIndex: currentWeekIndex,
        totalMinutes: totalMins,
        topGame,
        state: cellState,
      });

      if (dayOfWeek === 6) {
        currentWeekIndex++;
      }

      // Increment 1 day UTC
      currentDate.setUTCDate(currentDate.getUTCDate() + 1);
    }

    return { gridWeeks: weeks, monthLabels: months };
  }, [year, connectionDateStr, daysMap]);

  const handleCellInteraction = (
    e: React.MouseEvent<SVGRectElement> | React.TouchEvent<SVGRectElement>,
    cell: CellData
  ) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const formatted = cell.dateObj.toLocaleDateString("en-US", {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    });

    const hoverPayload: HoverData = {
      dateStr: cell.dateStr,
      formattedDate: formatted,
      totalMinutes: cell.totalMinutes,
      topGame: cell.topGame,
      state: cell.state,
    };

    setActiveHover(hoverPayload);

    // Keep tooltip clamped inside viewport on small mobile screens
    const rawX = rect.left + rect.width / 2;
    const padding = 125;
    const clampedX = Math.max(padding, Math.min(window.innerWidth - padding, rawX));

    setTooltip({
      ...hoverPayload,
      visible: true,
      x: clampedX,
      y: rect.top - 14,
    });
  };

  const handleMouseEnter = (
    e: React.MouseEvent<SVGRectElement>,
    cell: CellData
  ) => {
    handleCellInteraction(e, cell);
  };

  const handleClick = (
    e: React.MouseEvent<SVGRectElement> | React.TouchEvent<SVGRectElement>,
    cell: CellData
  ) => {
    handleCellInteraction(e, cell);
  };

  const handleMouseLeave = () => {
    setTooltip((prev) => ({ ...prev, visible: false }));
    setActiveHover(null);
  };

  const formatHoursDecimal = (mins: number) => {
    const hours = (mins / 60).toFixed(1);
    return `${hours} hrs`;
  };

  const formatPlaytimeDetail = (mins: number) => {
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    if (hours === 0) return `${remainingMins} mins`;
    if (remainingMins === 0) return `${hours} hrs`;
    return `${hours}h ${remainingMins}m`;
  };

  // Expanded larger tile size for prominent center presentation
  const cellSize = 16.5;
  const cellGap = 4;
  const colWidth = cellSize + cellGap;
  const rowHeight = cellSize + cellGap;

  return (
    <div className="heatmap-card">
      <div className="heatmap-header">
        <div className="heatmap-title-block">
          <div className="heatmap-title-row">
            <Swords size={22} className="text-steam-cyan" />
            <h2 className="heatmap-title">{en.heatmap.title}</h2>
            <div className="live-pulse-dot" />
          </div>
          <p className="heatmap-subtitle">{en.heatmap.subheading}</p>
        </div>

        {/* Live Hover HUD or Connected Status */}
        {activeHover ? (
          <div className="live-hover-hud">
            <Sparkles size={16} className="text-steam-green animate-pulse" />
            <span className="live-hud-date">{activeHover.formattedDate}:</span>
            {activeHover.state === "untracked" ? (
              <span className="live-hud-untracked">Pre-connection</span>
            ) : activeHover.totalMinutes === 0 ? (
              <span className="live-hud-zero">0.0 hrs played</span>
            ) : (
              <span className="live-hud-active">
                <strong>{formatHoursDecimal(activeHover.totalMinutes)}</strong>
                <span className="live-hud-sub"> ({formatPlaytimeDetail(activeHover.totalMinutes)})</span>
                {activeHover.topGame && (
                  <span className="live-hud-game">
                    {" "}• {activeHover.topGame.name} ({(activeHover.topGame.minutes_played / 60).toFixed(1)} hrs)
                  </span>
                )}
              </span>
            )}
          </div>
        ) : (
          <div className="connection-info">
            <Info size={15} className="text-steam-cyan" />
            <span>
              Connected since: <strong>{connectionDateStr}</strong>
            </span>
          </div>
        )}
      </div>

      <div className="heatmap-svg-wrapper">
        <svg
          width={gridWeeks.length * colWidth + 60}
          height={7 * rowHeight + 46}
          className="heatmap-svg"
        >
          <defs>
            {/* Pattern for untracked days */}
            <pattern
              id="untracked-stripe"
              width="6"
              height="6"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="6"
                stroke="#202b3c"
                strokeWidth="2.2"
              />
            </pattern>
          </defs>

          {/* Month Labels */}
          <g className="month-labels" transform="translate(42, 14)">
            {monthLabels.map((m, i) => (
              <text
                key={i}
                x={m.weekIndex * colWidth}
                y={0}
                className="heatmap-month-text"
              >
                {m.label}
              </text>
            ))}
          </g>

          {/* Day of Week Labels */}
          <g className="day-labels" transform="translate(4, 29)">
            <text x="0" y={1 * rowHeight + 13} className="heatmap-day-text">
              Mon
            </text>
            <text x="0" y={3 * rowHeight + 13} className="heatmap-day-text">
              Wed
            </text>
            <text x="0" y={5 * rowHeight + 13} className="heatmap-day-text">
              Fri
            </text>
          </g>

          {/* Grid Cells */}
          <g transform="translate(42, 24)">
            {gridWeeks.map((week, wIndex) =>
              week.map((cell) => {
                const x = wIndex * colWidth;
                const y = cell.dayOfWeek * rowHeight;
                return (
                  <rect
                    key={cell.dateStr}
                    x={x}
                    y={y}
                    width={cellSize}
                    height={cellSize}
                    rx={4}
                    className={`heatmap-cell cell-${cell.state}`}
                    fill={
                      cell.state === "untracked"
                        ? "url(#untracked-stripe)"
                        : undefined
                    }
                    onMouseEnter={(e) => handleMouseEnter(e, cell)}
                    onMouseLeave={handleMouseLeave}
                    onClick={(e) => handleClick(e, cell)}
                    onTouchEnd={(e) => handleClick(e, cell)}
                  />
                );
              })
            )}
          </g>
        </svg>
      </div>

      {/* Heatmap Footer & Legend */}
      <div className="heatmap-footer">
        <div className="legend-group">
          <span className="legend-label">{en.heatmap.legend_untracked}</span>
          <div className="legend-cell untracked" title="Not tracked yet (Before account connection)" />
        </div>

        <div className="legend-scale">
          <span className="legend-label">{en.heatmap.legend_less}</span>
          <div className="legend-cell zero" title="0 hrs" />
          <div className="legend-cell tier1" title="< 0.5 hrs (< 30 mins)" />
          <div className="legend-cell tier2" title="0.5 - 2 hrs" />
          <div className="legend-cell tier3" title="2 - 5 hrs" />
          <div className="legend-cell tier4" title="5+ hrs" />
          <span className="legend-label">{en.heatmap.legend_more}</span>
        </div>
      </div>

      {/* Dynamic Hover Tooltip displaying number of hours played */}
      {tooltip.visible && (
        <div
          className="heatmap-tooltip"
          style={{
            position: "fixed",
            left: `${tooltip.x}px`,
            top: `${tooltip.y}px`,
            transform: "translate(-50%, -100%)",
            pointerEvents: "none",
          }}
        >
          <div className="tooltip-header">
            <span className="tooltip-date">{tooltip.formattedDate}</span>
          </div>
          <div className="tooltip-body">
            {tooltip.state === "untracked" ? (
              <div className="tooltip-untracked">
                <Clock size={14} className="text-slate-400" />
                <span>
                  {en.heatmap.untracked_tile} (Joined {connectionDateStr})
                </span>
              </div>
            ) : tooltip.totalMinutes === 0 ? (
              <div className="tooltip-zero">
                <span className="tooltip-hours-badge zero">0.0 hrs</span>
                <span>{en.heatmap.no_playtime}</span>
              </div>
            ) : (
              <div className="tooltip-active">
                <div className="tooltip-hours-hero-row">
                  <div className="tooltip-hours-badge active">
                    <Zap size={14} className="text-steam-green" />
                    <strong>{formatHoursDecimal(tooltip.totalMinutes)}</strong>
                  </div>
                  <span className="tooltip-minutes-sub">
                    ({formatPlaytimeDetail(tooltip.totalMinutes)} total)
                  </span>
                </div>

                {tooltip.topGame && (
                  <div className="tooltip-top-game">
                    <Gamepad2 size={14} className="text-steam-cyan" />
                    <span className="tooltip-top-game-name">
                      {tooltip.topGame.name}
                    </span>
                    <span className="tooltip-top-game-hours">
                      {(tooltip.topGame.minutes_played / 60).toFixed(1)} hrs
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
