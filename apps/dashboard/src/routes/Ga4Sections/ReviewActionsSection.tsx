import { ShieldAlert } from "lucide-react";
import { useState, type ComponentType } from "react";

import { ActionPreviewCard } from "../../components/ActionPreviewCard";
import { MetricTile } from "../../components/OperatorPrimitives";
import { TraceLine } from "../../components/TraceLine";
import { ActionFocus } from "../ActionPanels";
import { Ga4MeasurementIssues } from "./MeasurementSection";
import type {
  ActionObject,
  ActionPreviewCardViewModel,
  Ga4DecisionCardComponent,
  Ga4DiagnosticsResponse
} from "./Shared";

export function Ga4ExpandableReviewPanel({
  data,
  trackingPreviewCards,
  DecisionCard,
  DiagnosticProof
}: {
  data: Ga4DiagnosticsResponse;
  trackingPreviewCards: ActionPreviewCardViewModel[];
  DecisionCard: Ga4DecisionCardComponent;
  DiagnosticProof: ComponentType<{ data: Ga4DiagnosticsResponse }>;
}) {
  const [showReview, setShowReview] = useState(false);

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Pełny przegląd GA4
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Pierwszy ekran pokazuje status pomiaru i najważniejszą decyzję. Rozwiń pełny
            przegląd, gdy chcesz zobaczyć problemy pomiaru, dowody, podgląd przeglądu i bramę
            bezpieczeństwa GA4.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Pomiar" value={data.operator_summary.measurement_issue_count} />
          <MetricTile label="Dowody" value={data.evidence_summary_label} />
          <MetricTile label="Podglądy" value={trackingPreviewCards.length} />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowReview((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showReview ? "Ukryj pełny przegląd GA4" : "Pokaż pełny przegląd GA4"}
      </button>

      {showReview ? (
        <div className="mt-4 grid gap-6">
          <Ga4MeasurementIssues data={data} DecisionCard={DecisionCard} />
          <DiagnosticProof data={data} />
          {trackingPreviewCards.length > 0 ? (
            <section className="rounded-md border border-line bg-white p-4">
              <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
                    Podgląd przeglądu GA4
                  </h2>
                  <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
                    Kolejka akcji do sprawdzenia. Pokazuje stronę wejścia, źródło ruchu i
                    kampanię do kontroli bez zapisu zmian w GA4.
                  </p>
                </div>
                <MetricTile label="Pozycje" value={trackingPreviewCards.length} />
              </div>
              <div className="grid gap-3 xl:grid-cols-2">
                {trackingPreviewCards.slice(0, 4).map((card) => (
                  <ActionPreviewCard key={card.id} card={card} />
                ))}
              </div>
            </section>
          ) : null}

          <section className="rounded-md border border-line bg-white p-4">
            <div className="mb-3 flex items-start gap-3">
              <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
                <ShieldAlert aria-hidden="true" size={18} />
              </div>
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
                  Brama bezpieczeństwa GA4
                </h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  WILQ może przygotować ocenę jakości ruchu i checklistę pomiaru, ale nie może
                  uznać wyniku za problem kampanii bez konwersji, kosztów i sprawdzenia w WILQ.
                </p>
              </div>
            </div>
            <TraceLine
              label="Nie wolno twierdzić"
              values={data.sections.flatMap((section) => section.blocked_claim_labels)}
            />
          </section>
        </div>
      ) : null}
    </section>
  );
}

export function Ga4ExpandableActionsPanel({
  actions,
  actionSummaryLabel
}: {
  actions: ActionObject[];
  actionSummaryLabel: string;
}) {
  const [showActions, setShowActions] = useState(false);
  const actionCountLabel =
    actionSummaryLabel.trim() ||
    "WILQ nie podał etykiety akcji; nie traktuj tej decyzji jako gotowej do działania";
  const actionCountSentence = `WILQ pokazuje dla GA4: ${actionCountLabel}.`;

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Akcje do sprawdzenia
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {actionCountSentence} Otwórz ją dopiero wtedy, gdy chcesz zapisać przegląd człowieka,
            wygenerować podgląd zmian albo sprawdzić warunki bezpiecznego zapisu.
          </p>
        </div>
        <MetricTile label="Akcje" value={actionCountLabel} />
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
