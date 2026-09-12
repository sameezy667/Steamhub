/**
 * @file Heatmap.tsx
 * @description 52-week contribution heatmap rendering 3 distinct states (untracked, zero-activity, activity tiers) with rich tooltips
 * @module frontend/components
 */

import React, { useMemo, useState } from "react";
import { Clock, Gamepad2, Info } from "lucide-react";
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

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  dateStr: string;
  formattedDate: string;
  totalMinutes: number;
  topGame: TopGameInfo | null;
  state: string;
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

  const handleMouseEnter = (
    e: React.MouseEvent<SVGRectElement>,
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

    setTooltip({
      visible: true,
      x: rect.left + rect.width / 2,
      y: rect.top - 12,
      dateStr: cell.dateStr,
      formattedDate: formatted,
      totalMinutes: cell.totalMinutes,
      topGame: cell.topGame,
      state: cell.state,
    });
  };

  const handleMouseLeave = () => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  };

  const formatPlaytime = (mins: number) => {
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    if (hours === 0) return `${remainingMins} mins`;
    if (remainingMins === 0) return `${hours} hrs`;
    return `${hours} hrs ${remainingMins} mins`;
  };

  const cellSize = 13;
  const cellGap = 3;
  const colWidth = cellSize + cellGap;
  const rowHeight = cellSize + cellGap;

  return (
    <div className="heatmap-card">
      <div className="heatmap-header">
        <div>
          <h2 className="heatmap-title">{en.heatmap.title}</h2>
          <p className="heatmap-subtitle">{en.heatmap.subheading}</p>
        </div>
        <div className="connection-info">
          <Info size={14} className="text-steam-cyan" />
          <span>
            Connected since: <strong>{connectionDateStr}</strong>
          </span>
        </div>
      </div>

      <div className="heatmap-svg-wrapper">
        <svg
          width={gridWeeks.length * colWidth + 50}
          height={7 * rowHeight + 35}
          className="heatmap-svg"
        >
          <defs>
            {/* Pattern for untracked days */}
            <pattern
              id="untracked-stripe"
              width="4"
              height="4"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="4"
                stroke="#2a3847"
                strokeWidth="1.5"
              />
            </pattern>
          </defs>

          {/* Month Labels */}
          <g className="month-labels" transform="translate(36, 12)">
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
          <g className="day-labels" transform="translate(0, 24)">
            <text x="5" y={1 * rowHeight + 10} className="heatmap-day-text">
              Mon
            </text>
            <text x="5" y={3 * rowHeight + 10} className="heatmap-day-text">
              Wed
            </text>
            <text x="5" y={5 * rowHeight + 10} className="heatmap-day-text">
              Fri
            </text>
          </g>

          {/* Grid Cells */}
          <g transform="translate(36, 20)">
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
                    rx={2.5}
                    className={`heatmap-cell cell-${cell.state}`}
                    fill={
                      cell.state === "untracked"
                        ? "url(#untracked-stripe)"
                        : undefined
                    }
                    onMouseEnter={(e) => handleMouseEnter(e, cell)}
                    onMouseLeave={handleMouseLeave}
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
          <div className="legend-cell untracked" title="Not tracked yet" />
        </div>

        <div className="legend-scale">
          <span className="legend-label">{en.heatmap.legend_less}</span>
          <div className="legend-cell zero" title="0 mins" />
          <div className="legend-cell tier1" title="< 30 mins" />
          <div className="legend-cell tier2" title="30m - 2 hrs" />
          <div className="legend-cell tier3" title="2 hrs - 5 hrs" />
          <div className="legend-cell tier4" title="5+ hrs" />
          <span className="legend-label">{en.heatmap.legend_more}</span>
        </div>
      </div>

      {/* Dynamic Hover Tooltip */}
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
                  {en.heatmap.untracked_tile} ({en.heatmap.untracked_desc}{" "}
                  {connectionDateStr})
                </span>
              </div>
            ) : tooltip.totalMinutes === 0 ? (
              <div className="tooltip-zero">
                <span>{en.heatmap.no_playtime}</span>
              </div>
            ) : (
              <div className="tooltip-active">
                <div className="tooltip-total">
                  <Clock size={14} className="text-steam-green" />
                  <strong>{formatPlaytime(tooltip.totalMinutes)}</strong>
                  <span>{en.heatmap.played}</span>
                </div>
                {tooltip.topGame && (
                  <div className="tooltip-top-game">
                    <Gamepad2 size={14} className="text-steam-cyan" />
                    <span>
                      {en.heatmap.top_game}:{" "}
                      <strong>{tooltip.topGame.name}</strong> (
                      {formatPlaytime(tooltip.topGame.minutes_played)})
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
