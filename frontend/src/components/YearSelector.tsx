/**
 * @file YearSelector.tsx
 * @description Year filter tabs with enlarged aggregate annual hours, active days, and sleek gaming metrics
 * @module frontend/components
 */

import React from "react";
import { Calendar, Timer, Trophy } from "lucide-react";
import en from "../locales/en.json";

interface YearSelectorProps {
  selectedYear: number;
  availableYears: number[];
  totalYearMinutes: number;
  activeDaysCount: number;
  onSelectYear: (year: number) => void;
}

export const YearSelector: React.FC<YearSelectorProps> = ({
  selectedYear,
  availableYears,
  totalYearMinutes,
  activeDaysCount,
  onSelectYear,
}) => {
  const totalHours = (totalYearMinutes / 60).toFixed(1);
  const totalHoursInt = Math.floor(totalYearMinutes / 60);
  const remainingMinutes = totalYearMinutes % 60;

  return (
    <div className="year-selector-card">
      <div className="year-tabs">
        {availableYears.map((yr) => (
          <button
            key={yr}
            onClick={() => onSelectYear(yr)}
            className={`year-tab ${selectedYear === yr ? "active" : ""}`}
          >
            <Calendar size={16} />
            <span>{yr}</span>
            {selectedYear === yr && <div className="year-tab-indicator" />}
          </button>
        ))}
      </div>

      <div className="year-metrics">
        <div className="metric-pill metric-hours">
          <div className="metric-icon-box cyan">
            <Timer size={20} />
          </div>
          <div className="metric-text">
            <span className="metric-label">{en.heatmap.total_year} {selectedYear}</span>
            <div className="metric-value-row">
              <strong className="metric-value text-glow-cyan">{totalHours} hrs</strong>
              <span className="metric-value-sub">({totalHoursInt}h {remainingMinutes}m)</span>
            </div>
          </div>
        </div>

        <div className="metric-pill metric-days">
          <div className="metric-icon-box emerald">
            <Trophy size={20} />
          </div>
          <div className="metric-text">
            <span className="metric-label">Active Gaming Days</span>
            <div className="metric-value-row">
              <strong className="metric-value text-glow-green">{activeDaysCount} days</strong>
              <span className="metric-value-sub">recorded</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
