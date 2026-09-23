/** Canonical operator order for one exact ActionObject. */
export const ACTION_LIFECYCLE_ORDER = [
  "validate",
  "preview",
  "review",
  "confirm_impact_apply"
] as const;
