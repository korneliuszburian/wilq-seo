import { useState } from "react";

import { MetricTile } from "../../components/OperatorPrimitives";
import type { ActionObject } from "../../lib/api";
import { ActionFocus } from "../ActionPanels";
import { MerchantFeedSafetyPanel } from "./FeedSafetySection";
import {
  MerchantDiagnosticProof,
  MerchantOperatorSummary,
  MerchantUnknowns
} from "./OperatorSummarySection";
import {
  MerchantPriceImpactReadiness,
  MerchantProductPerformanceReadiness,
  MerchantProductSampleReadiness
} from "./ProductSections";
import type { MerchantDiagnosticsResponse } from "./shared";

export function MerchantExpandableReviewPanel({ data }: { data: MerchantDiagnosticsResponse }) {
  const [showReview, setShowReview] = useState(false);

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Pełny przegląd Merchant
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Pierwszy ekran pokazuje status i najważniejszy problem pliku produktowego. Rozwiń
            pełny przegląd, gdy chcesz zobaczyć kolejkę decyzji, gotowość próbek,
            powiązania z reklamami/analityką, ograniczenia i techniczne podstawy decyzji.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
          <MetricTile label="Zgłoszenia" value={data.operator_summary.reported_issue_occurrences} />
          <MetricTile label="Podstawa" value={data.evidence_summary_label} />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowReview((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showReview ? "Ukryj pełny przegląd Merchant" : "Pokaż pełny przegląd Merchant"}
      </button>

      {showReview ? (
        <div className="mt-4 grid gap-6">
          <MerchantOperatorSummary data={data} />
          <MerchantProductSampleReadiness data={data} />
          <MerchantProductPerformanceReadiness data={data} />
          <MerchantPriceImpactReadiness data={data} />
          <MerchantUnknowns data={data} />
          <MerchantDiagnosticProof data={data} />
          <MerchantFeedSafetyPanel data={data} />
        </div>
      ) : null}
    </section>
  );
}

export function MerchantExpandableActionsPanel({
  actions,
  actionSummaryLabel
}: {
  actions: ActionObject[];
  actionSummaryLabel: string;
}) {
  const [showActions, setShowActions] = useState(false);

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Akcje do sprawdzenia
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ pokazuje dla Merchant: {actionSummaryLabel}. Otwórz tę sekcję dopiero wtedy, gdy
            chcesz zapisać przegląd człowieka, wygenerować podgląd zmian albo
            sprawdzić warunki bezpiecznego zapisu.
          </p>
        </div>
        <MetricTile label="Akcje" value={actionSummaryLabel} />
      </div>

      <button
        type="button"
        onClick={() => setShowActions((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showActions ? "Ukryj akcje do sprawdzenia" : "Pokaż akcje do sprawdzenia"}
      </button>

      {showActions ? (
        <div className="mt-4">
          <ActionFocus actions={actions} />
        </div>
      ) : null}
    </section>
  );
}

