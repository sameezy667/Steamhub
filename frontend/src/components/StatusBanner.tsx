/**
 * @file StatusBanner.tsx
 * @description Notification banner warning users when Steam game details or profile are private
 * @module frontend/components
 */

import React from "react";
import { AlertTriangle, ExternalLink, ShieldAlert } from "lucide-react";
import en from "../locales/en.json";

interface StatusBannerProps {
  visibilityState: number | null | undefined;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({ visibilityState }) => {
  // If visibilityState is 3 (public) or undefined, do not show warning
  if (visibilityState === 3 || visibilityState === undefined) {
    return null;
  }

  return (
    <div className="status-banner-card">
      <div className="banner-icon-container">
        <ShieldAlert className="text-amber-400" size={24} />
      </div>
      <div className="banner-content">
        <div className="banner-title-row">
          <h3 className="banner-title">{en.status.private}</h3>
          <span className="banner-badge">Action Required</span>
        </div>
        <p className="banner-message">{en.status.private_notice}</p>
        <div className="banner-steps">
          <AlertTriangle size={16} className="text-amber-300" />
          <span>{en.status.private_steps}</span>
        </div>
      </div>
      <div className="banner-action">
        <a
          href="https://steamcommunity.com/my/edit/settings"
          target="_blank"
          rel="noopener noreferrer"
          className="btn-privacy-link"
        >
          <span>Steam Privacy Settings</span>
          <ExternalLink size={14} />
        </a>
      </div>
    </div>
  );
};
