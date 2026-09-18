import { describe, expect, it } from "vitest";
import { z, type ZodTypeAny } from "zod";

import {
  AdsDiagnosticsResponseSchema,
  AhrefsDiagnosticsResponseSchema,
  Ga4DiagnosticsResponseSchema,
  LocaloDiagnosticsResponseSchema,
  MerchantDiagnosticsResponseSchema
} from "./index";

const readiness = {
  state: "partial",
  state_label: "Dane częściowe",
  reason: "Część danych wymaga sprawdzenia.",
  coverage_label: "Pokazano potwierdzone metryki.",
  refresh_allowed: false,
  safe_next_step: "Sprawdź zakres danych przed decyzją.",
  factual_metric_count: 1,
      factual_metrics: [
    {
      name: "sessions",
      metric_label: "sesje",
      value: 12,
      period: "connector_refresh",
      period_label: "okres odświeżenia źródła",
      source_connector: "test_connector",
      source_connector_label: "Źródło testowe",
      evidence_id: "ev_test_readiness",
      previous_value: 10,
      previous_evidence_id: "ev_test_readiness_previous",
      previous_collected_at: "2026-06-16T10:00:00Z"
    }
  ],
  evidence_ids: ["ev_test_readiness"],
  connector_id: "test_connector",
  connector_label: "Źródło testowe",
  latest_refresh_id: "refresh_test_readiness"
};

const responseSchemas = [
  ["Ads", AdsDiagnosticsResponseSchema],
  ["GA4", Ga4DiagnosticsResponseSchema],
  ["Merchant", MerchantDiagnosticsResponseSchema],
  ["Ahrefs", AhrefsDiagnosticsResponseSchema],
  ["Localo", LocaloDiagnosticsResponseSchema]
] as const;

describe("diagnostic data readiness contract", () => {
  it.each(responseSchemas)(
    "%s preserves readiness and requires the API-owned field",
    (_name, responseSchema) => {
      const schemaShape = (responseSchema as z.ZodObject<z.ZodRawShape>).shape;
      const readinessSchema = schemaShape.data_readiness as ZodTypeAny | undefined;

      expect(readinessSchema).toBeDefined();
      if (!readinessSchema) return;
      expect(readinessSchema.safeParse(readiness).success).toBe(true);
      expect(readinessSchema.safeParse(undefined).success).toBe(false);

      const parsed = responseSchema.partial().safeParse({ data_readiness: readiness });
      expect(parsed.success).toBe(true);
      expect(parsed.success && parsed.data.data_readiness).toMatchObject(readiness);
    }
  );
});
