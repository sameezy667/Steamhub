/**
 * @file YearSelector.tsx
 * @description Year filter tabs with aggregate annual hours, active days, and streaks
 * @module frontend/components
 */

import React from "react";
import { Calendar, Clock, Flame } from "lucide-react";
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
  const totalHours = Math.floor(totalYearMinutes / 60);
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
          </button>
        ))}
      </div>

      <div className="year-metrics">
        <div className="metric-pill">
          <Clock size={16} className="text-steam-cyan" />
          <div className="metric-text">
            <span className="metric-label">{en.heatmap.total_year} {selectedYear}</span>
            <strong className="metric-value">
              {totalHours} {en.heatmap.hours} {remainingMinutes > 0 ? `${remainingMinutes} ${en.heatmap.minutes}` : ""}
            </strong>
          </div>
        </div>

        <div className="metric-pill">
          <Flame size={16} className="text-steam-green" />
          <div className="metric-text">
            <span className="metric-label">Active Gaming Days</span>
            <strong className="metric-value">{activeDaysCount} days</strong>
          </div>
        </div>
      </div>
    </div>
  );
};
