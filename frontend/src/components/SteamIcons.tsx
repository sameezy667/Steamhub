/**
 * @file SteamIcons.tsx
 * @description Custom SVG gaming and authentic Steam brand vector icons
 * @module frontend/components
 */

import React from "react";

interface IconProps {
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}

export const SteamLogo: React.FC<IconProps> = ({ size = 24, className = "", style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
    style={style}
    xmlns="http://www.w3.org/2000/svg"
  >
    <path d="M11.979 0C5.64 0 .463 4.908.026 11.16l5.727 2.368a3.523 3.523 0 0 1 2.455-.705l3.298-4.78a4.426 4.426 0 0 1-.026-.474 4.43 4.43 0 1 1 4.43 4.43 4.453 4.453 0 0 1-1.397-.225l-4.708 3.37a3.526 3.526 0 0 1-.65 2.127 3.535 3.535 0 0 1-4.99 1.018 3.536 3.536 0 0 1-1.026-4.91L.002 12.015A11.986 11.986 0 1 0 11.979 0zm-7.85 15.93a2.355 2.355 0 1 0 2.356 2.356 2.358 2.358 0 0 0-2.356-2.356zm11.73-10.27a3.25 3.25 0 1 0 3.25 3.25 3.254 3.254 0 0 0-3.25-3.25z" />
  </svg>
);

export const SteamAvatarFallback: React.FC<IconProps> = ({ size = 38, className = "" }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: "50%",
      background: "linear-gradient(135deg, #1b2838 0%, #171a21 100%)",
      border: "2px solid #66c0f4",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "#66c0f4",
    }}
    className={className}
  >
    <SteamLogo size={size * 0.55} />
  </div>
);
