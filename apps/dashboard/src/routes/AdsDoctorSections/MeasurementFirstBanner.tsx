import { AlertTriangle, CircleSlash } from "lucide-react";

import type {
  AdsDiagnosticsResponse,
  DemandGenReadinessContract,
  Ga4DiagnosticsResponse
} from "../../lib/api";
import { uniqueLabels } from "./formatters";

export function MeasurementFirstBanner({
  data,
  ga4Data,
  demandGenData
}: {
  data: AdsDiagnosticsResponse;
  ga4Data: Ga4DiagnosticsResponse | null;
  demandGenData: DemandGenReadinessContract | null;
}) {
  const ga4Blockers = ga4Data?.operator_summary.blocked_claim_labels ?? [];
  const adsMissing = data.operator_summary.missing_read_contract_labels;
  const demandGenMissing = demandGenData?.missing_read_contract_labels ?? [];
  const blockers = uniqueLabels([...ga4Blockers, ...adsMissing, ...demandGenMissing]).slice(0, 4);

  return (
    <section className="my-5 overflow-hidden rounded-md border border-red-200 bg-red-50 shadow-sm">
      <div className="grid gap-0 lg:grid-cols-[1.1fr_1fr]">
        <div className="border-b border-red-200 p-4 lg:border-b-0 lg:border-r">
          <div className="flex items-start gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-risk">
              <AlertTriangle aria-hidden="true" size={20} />
            </span>
            <div>
              <div className="text-sm font-semibold uppercase tracking-normal text-risk">
                Najpierw pomiar
              </div>
              <h2 className="mt-1 text-lg font-semibold text-ink">
                ROAS, przychód, waste i konwersje są zablokowane do czasu potwierdzenia danych.
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-700">
                {ga4Data?.conversion_readiness_contract.summary ?? data.strict_instruction}
              </p>
            </div>
          </div>
        </div>
        <div className="p-4">
          <div className="text-sm font-semibold text-ink">Co blokuje wniosek</div>
          <div className="mt-3 grid gap-2">
            {blockers.length > 0 ? (
              blockers.map((blocker) => (
                <div key={blocker} className="flex items-center gap-2 text-sm text-slate-700">
                  <CircleSlash aria-hidden="true" size={16} className="shrink-0 text-risk" />
                  <span>{blocker}</span>
                </div>
              ))
            ) : (
              <div className="flex items-center gap-2 text-sm text-slate-700">
                <CircleSlash aria-hidden="true" size={16} className="shrink-0 text-risk" />
                <span>Brak jawnej bramki pomiaru w odczycie. Zatrzymaj wnioski i sprawdź źródła.</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
