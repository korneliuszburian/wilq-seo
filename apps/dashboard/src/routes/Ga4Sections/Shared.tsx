import type { ComponentType } from "react";

import type {
  ActionObject,
  ActionPreviewCardViewModel,
  Ga4DiagnosticsResponse
} from "../../lib/api";

export type { ActionObject, ActionPreviewCardViewModel, Ga4DiagnosticsResponse };

export type Ga4DecisionItem = Ga4DiagnosticsResponse["decision_queue"][number];
export type Ga4MetricFact =
  Ga4DiagnosticsResponse["sections"][number]["metric_facts"][number];
export type Ga4DecisionCardComponent = ComponentType<{ decision: Ga4DecisionItem }>;
