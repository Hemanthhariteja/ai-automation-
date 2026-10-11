// Validated via the dataviz skill's scripts/validate_palette.js against this
// app's actual panel surface colors (#ffffff light / #1b1a21 dark). See the
// Phase 12 summary for the exact validator invocations and results.

export const CATEGORICAL = {
  light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
  dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
};

// Ordinal ramp (single hue, monotone lightness) for severity tiers: low / medium-normal / high
export const ORDINAL = {
  light: ["#86b6ef", "#2a78d6", "#184f95"],
  dark: ["#6da7ec", "#3987e5", "#1c5cab"],
};

// Fixed status scale — mode-invariant, reserved for good/bad state, never reused for identity
export const STATUS = {
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
};

export const INK = {
  light: { primary: "#0b0b0b", secondary: "#52514e", muted: "#898781", grid: "#e1e0d9", axis: "#c3c2b7" },
  dark: { primary: "#ffffff", secondary: "#c3c2b7", muted: "#898781", grid: "#2c2c2a", axis: "#383835" },
};

export const SURFACE = { light: "#ffffff", dark: "#1b1a21" };

// Fixed per-label colors so a category keeps its color even if the visible
// set changes (e.g. a status with zero leads simply doesn't appear).
const STATUS_LABEL_SLOT = { new: 0, contacted: 1, qualified: 2, won: 5, lost: 7 };
const INTENT_LABEL_SLOT = {
  quote_request: 0,
  booking_request: 1,
  general_inquiry: 2,
  support_request: 3,
  information_request: 4,
  complaint: 7,
};

export function statusColor(label, scheme) {
  const slot = STATUS_LABEL_SLOT[label];
  return slot != null ? CATEGORICAL[scheme][slot] : INK[scheme].muted;
}

export function intentColor(label, scheme) {
  const slot = INTENT_LABEL_SLOT[label];
  return slot != null ? CATEGORICAL[scheme][slot] : INK[scheme].muted;
}
