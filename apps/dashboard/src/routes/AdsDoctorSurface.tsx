import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  ActionObject,
  AdsDiagnosticsResponse,
  getActions,
  getAdsDiagnosticsSummary,
  getConnectors
} from "../lib/api";
import {
  BlockerNotice,
  LoadingBand,
  MetricTile,
  PlainChipRow
} from "../components/OperatorPrimitives";
import { AdsMetricEvidencePanel } from "../components/AdsMetricEvidencePanel";
import { AdsOperatorSummary } from "../components/AdsOperatorSummaryPanels";
import { AdsCondensedDecisionPanel, AdsMarketSnapshot } from "../components/AdsOverviewPanels";
import { TraceLine } from "../components/TraceLine";
import { ActionFocus } from "./ActionPanels";

type AdsBlockedHandoff = NonNullable<AdsDiagnosticsResponse["blocked_handoff"]>;

export function AdsDoctorSurface() {
  const diagnostics = useQuery({
    queryKey: ["ads-diagnostics", "summary"],
    queryFn: getAdsDiagnosticsSummary
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });
  const connectors = useQuery({
    queryKey: ["connectors"],
    queryFn: getConnectors
  });

  if (diagnostics.isLoading || actions.isLoading || connectors.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać danych Ads. WILQ nie może udawać diagnozy bez danych." />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się pobrać akcji do sprawdzenia. Odśwież widok albo sprawdź status WILQ." />
      </main>
    );
  }
  if (connectors.error || !connectors.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się pobrać statusu źródeł danych. Odśwież widok albo sprawdź status WILQ." />
      </main>
    );
  }

  const data = diagnostics.data;
  const currencyCode = data.account_currency_read_contract.currency_code ?? undefined;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const latestRefresh = data.latest_refresh;
  const blockedDecisionCount = data.decision_queue.filter(
    (decision) => decision.status === "blocked"
  ).length;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Google Ads</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Google Ads z WILQ. Pokazuje, co marketer może
            uczciwie sprawdzić na podstawie kampanii i zapytań oraz które wnioski
            pozostają zablokowane bez kolejnych danych.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
          <MetricTile label="Blokady" value={blockedDecisionCount} />
          <MetricTile label="Dowody" value={data.evidence_summary_label} />
          <MetricTile label="Waluta" value={currencyCode ?? "waluta do potwierdzenia"} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Google Ads
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <PlainChipRow
            values={[
              `${data.connector.label}: ${data.connector_status_label}`,
              data.live_data_status_label,
              data.freshness_assessment.state_label,
              latestRefresh ? `ostatni odczyt: ${data.latest_refresh_status_label}` : null
            ]}
          />
        </div>
        <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-sm leading-6 text-slate-700">
          <p>{data.freshness_assessment.summary}</p>
          <p className="mt-1 font-medium text-ink">{data.freshness_assessment.next_step}</p>
        </div>
        {latestRefresh?.errors.length ? (
          <div className="mt-3 rounded-md border border-risk/30 bg-risk/10 p-3 text-sm text-risk">
            {latestRefresh.errors[0]}
          </div>
        ) : null}
      </section>

      {data.blocked_handoff ? (
        <AdsBlockedHandoffPanel handoff={data.blocked_handoff} />
      ) : null}

      <AdsCondensedDecisionPanel data={data} currencyCode={currencyCode} />
      <AdsMarketSnapshot data={data} currencyCode={currencyCode} />
      <AdsExpandableReviewPanel data={data} currencyCode={currencyCode} />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <AdsExpandableActionsPanel
            actions={routeActions}
            actionSummaryLabel={data.action_summary_label}
          />
        </div>
      ) : null}

    </main>
  );
}

function AdsExpandableActionsPanel({
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
            WILQ pokazuje dla Google Ads: {actionSummaryLabel}. Otwórz tę sekcję dopiero wtedy, gdy
            chcesz zapisać przegląd człowieka, wygenerować podgląd zmian albo
            sprawdzić warunki zapisu akcji.
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

function AdsExpandableReviewPanel({
  data,
  currencyCode
}: {
  data: AdsDiagnosticsResponse;
  currencyCode: string | undefined;
}) {
  const [showDeepReview, setShowDeepReview] = useState(false);
  const summary = data.operator_summary;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Pełny przegląd Ads
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Pierwszy ekran pokazuje decyzję i skrót odczytu. Rozwiń pełny przegląd,
            gdy chcesz przejrzeć gotowość obszarów, karty decyzji, zapytania,
            rekomendacje i szczegółowe dowody.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Gotowe" value={summary.ready_area_count} />
          <MetricTile label="Blokady" value={summary.blocked_area_count} />
          <MetricTile label="Akcje" value={summary.action_summary_label} />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowDeepReview((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showDeepReview ? "Ukryj pełny przegląd Ads" : "Pokaż pełny przegląd Ads"}
      </button>

      {showDeepReview ? (
        <div className="mt-4 grid gap-6">
          <AdsOperatorSummary data={data} />
          <AdsMetricEvidencePanel data={data} currencyCode={currencyCode} />
        </div>
      ) : null}
    </section>
  );
}

function AdsBlockedHandoffPanel({
  handoff
}: {
  handoff: AdsBlockedHandoff;
}) {
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Przekazanie blokady Ads
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{handoff.title}</h2>
        </div>
        <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
          {handoff.status_label}
        </span>
      </div>
      <p className="text-sm leading-6 text-slate-700">{handoff.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{handoff.marketer_message}</p>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Ścieżka naprawy</h3>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-6 text-slate-700">
            {handoff.repair_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Co wolno pokazać w demo</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700">
            {handoff.allowed_demo_claims.map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Dowody" values={[handoff.evidence_summary_label]} />
        <TraceLine label="Źródła" values={handoff.source_connector_labels} />
        <TraceLine
          label="Akcje do sprawdzenia"
          values={[handoff.action_summary_label]}
          empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczny przegląd Ads."
        />
        <TraceLine label="Nie wolno twierdzić" values={handoff.blocked_claim_labels} />
      </div>
    </section>
  );
}
