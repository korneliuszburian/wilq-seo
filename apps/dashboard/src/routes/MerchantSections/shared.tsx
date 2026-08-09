import type { MerchantDiagnosticsResponse } from "../../lib/api";

export type { MerchantDiagnosticsResponse };

export type MerchantDecisionItem = MerchantDiagnosticsResponse["decision_queue"][number];
export type MerchantProductPerformanceRow =
  MerchantDiagnosticsResponse["product_performance_readiness"]["performance_rows"][number];
