import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  AlertTriangle,
  Boxes,
  CheckCircle2,
  ClipboardList,
  RefreshCw,
  ShieldAlert,
  ShoppingCart
} from "lucide-react";

import {
  ActionObject,
  getActions,
  getMerchantDiagnostics,
  MerchantDiagnosticsResponse
} from "../lib/api";
import {
  BlockerNotice,
  LabelChipRow,
  LoadingBand,
  MetricTile,
  PlainChipRow
} from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import { ActionPreviewCard } from "../components/ActionPreviewCard";
import { ActionFocus } from "./ActionPanels";
import { tacticalContextPairs } from "./TacticalQueuePanel";

type MerchantDecisionItem = MerchantDiagnosticsResponse["decision_queue"][number];
type MerchantProductPerformanceRow =
  MerchantDiagnosticsResponse["product_performance_readiness"]["performance_rows"][number];

export function MerchantDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["merchant-diagnostics"],
    queryFn: getMerchantDiagnostics
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });

  if (diagnostics.isLoading || actions.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać danych Merchant. Ten widok nie może udawać wniosków o pliku produktowym bez WILQ." />
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

  const data = diagnostics.data;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <MerchantOperatingViewport data={data} />

      <MerchantExpandableReviewPanel data={data} />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <MerchantExpandableActionsPanel
            actions={routeActions}
            actionSummaryLabel={data.action_summary_label}
          />
        </div>
      ) : null}
    </main>
  );
}

function MerchantOperatingViewport({ data }: { data: MerchantDiagnosticsResponse }) {
  const primaryDecision = primaryMerchantDecision(data);
  const stale = data.freshness_assessment.requires_refresh;
  const criticalBlockedClaims = uniqueValues([
    ...data.operator_summary.blocked_claim_labels,
    ...(primaryDecision?.blocked_claim_labels ?? [])
  ]).slice(0, 4);

  return (
    <>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal text-ink">Produkty</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Merchant Center, plik produktowy i bezpieczna kolejka problemów produktów.
          </p>
        </div>
      </div>

      <section className="mb-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MerchantStatCard
          icon={<ShoppingCart aria-hidden="true" size={22} />}
          value={data.product_count ?? 0}
          label="produktów w odczycie"
          cta="Zobacz kolejkę"
          tone="blue"
        />
        <MerchantStatCard
          icon={<AlertTriangle aria-hidden="true" size={22} />}
          value={data.operator_summary.reported_issue_occurrences}
          label="zgłoszeń problemów"
          cta="Wymagają przeglądu"
          tone="red"
        />
        <MerchantStatCard
          icon={<ClipboardList aria-hidden="true" size={22} />}
          value={data.decision_queue.length}
          label="decyzji produktowych"
          cta={data.action_summary_label}
          tone="amber"
        />
        <MerchantStatCard
          icon={<RefreshCw aria-hidden="true" size={22} />}
          value={stale ? `${Math.round(data.freshness_assessment.age_hours ?? 0)}h` : "OK"}
          label="świeżość danych"
          cta={data.freshness_assessment.state_label}
          tone={stale ? "purple" : "green"}
        />
      </section>

      <section className="mb-6 rounded-md border border-line bg-white px-4 py-3">
        <div className="grid gap-3 text-sm text-slate-700 md:grid-cols-4">
          <MerchantSourceStatus label="Merchant" value={data.connector_status_label} tone="green" />
          <MerchantSourceStatus
            label="Odczyt"
            value={data.latest_refresh_status_label ?? "brak ostatniego odczytu"}
            tone={stale ? "amber" : "green"}
          />
          <MerchantSourceStatus label="Dane" value={data.live_data_status_label} tone="green" />
          <MerchantSourceStatus label="Dowody" value={data.evidence_summary_label} tone="blue" />
        </div>
      </section>

      <section className="mb-6 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <article className="rounded-md border border-line bg-white shadow-sm">
          <div className="flex min-h-12 items-center justify-between gap-3 border-b border-action/20 bg-blue-50 px-4 py-3">
            <h2 className="text-base font-semibold text-ink">Następna najlepsza praca</h2>
            <StatusBadge value={primaryDecision?.priority <= 20 ? "high" : "medium"} label={primaryDecision?.priority_label ?? "priorytet"} />
          </div>
          <div className="p-4">
            {primaryDecision ? (
              <div className="flex items-start gap-3">
                <div className="rounded-full bg-blue-100 p-3 text-action">
                  <Boxes aria-hidden="true" size={24} />
                </div>
                <div className="min-w-0">
                  <h3 className="text-lg font-semibold leading-6 text-ink">{primaryDecision.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{primaryDecision.summary}</p>
                  <div className="mt-4 grid gap-3 rounded-md border border-line bg-slate-50 p-3 md:grid-cols-2">
                    <MetricTile
                      label="Zakres"
                      value={primaryDecision.issue_type_label ?? primaryDecision.decision_type_label}
                    />
                    <MetricTile label="Dowody" value={primaryDecision.evidence_summary_label} />
                  </div>
                  <h4 className="mt-4 text-sm font-semibold text-ink">Najbezpieczniejszy następny krok</h4>
                  <p className="mt-1 text-sm leading-6 text-slate-700">
                    {primaryDecision.next_step}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <a
                      href={primaryDecision.action_ids[0] ? `/actions/${primaryDecision.action_ids[0]}` : "#merchant-queue"}
                      className="inline-flex h-10 items-center rounded-md bg-action px-4 text-sm font-semibold text-white hover:bg-blue-700"
                    >
                      Otwórz pracę
                    </a>
                    <a
                      href="#merchant-queue"
                      className="inline-flex h-10 items-center rounded-md border border-action/30 bg-white px-4 text-sm font-semibold text-action hover:bg-blue-50"
                    >
                      Pokaż kolejkę
                    </a>
                  </div>
                </div>
              </div>
            ) : (
              <BlockerNotice message="Brak decyzji Merchant w WILQ. Najpierw uruchom odczyt danych Merchant." />
            )}
          </div>
        </article>

        <article className="rounded-md border border-line bg-white shadow-sm">
          <div className="flex min-h-12 items-center justify-between gap-3 border-b border-risk/20 bg-red-50 px-4 py-3">
            <h2 className="text-base font-semibold text-ink">Blokady, których nie obchodź</h2>
            <StatusBadge value={stale ? "high" : "medium"} label={stale ? "dane nieświeże" : "review wymagany"} />
          </div>
          <div className="divide-y divide-line">
            <MerchantBlockerRow
              title={stale ? "Nieświeże dane Merchant" : "Dane Merchant dostępne"}
              detail={stale ? data.freshness_assessment.next_step : data.freshness_assessment.summary}
            />
            <MerchantBlockerRow
              title="Brak zapisu zmian bez audytu"
              detail="Najpierw review, podgląd zmian, potwierdzenie operatora i audyt."
            />
            <MerchantBlockerRow
              title="Liczniki to zgłoszenia, nie SKU"
              detail={data.operator_summary.count_semantics_label}
            />
          </div>
          <div className="p-4">
            <h3 className="text-sm font-semibold text-ink">Nie wolno dziś twierdzić</h3>
            <div className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
              {criticalBlockedClaims.map((claim) => (
                <span key={claim} className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-wait" />
                  {claim}
                </span>
              ))}
            </div>
          </div>
        </article>
      </section>

      <MerchantQueuePreview data={data} />
    </>
  );
}

function MerchantStatCard({
  icon,
  value,
  label,
  cta,
  tone
}: {
  icon: React.ReactNode;
  value: number | string;
  label: string;
  cta: string;
  tone: "blue" | "green" | "amber" | "red" | "purple";
}) {
  const toneClass = {
    blue: "bg-blue-100 text-action",
    green: "bg-emerald-100 text-emerald-700",
    amber: "bg-amber-100 text-amber-700",
    red: "bg-red-100 text-risk",
    purple: "bg-violet-100 text-violet-700"
  }[tone];
  return (
    <article className="rounded-md border border-line bg-white p-4 shadow-sm">
      <div className="flex items-center gap-4">
        <div className={`rounded-full p-3 ${toneClass}`}>{icon}</div>
        <div>
          <div className="text-2xl font-semibold text-ink">{formatMerchantValue(value)}</div>
          <div className="text-sm text-slate-700">{label}</div>
        </div>
      </div>
      <div className="mt-3 text-sm font-medium text-action">{cta}</div>
    </article>
  );
}

function MerchantSourceStatus({
  label,
  value,
  tone
}: {
  label: string;
  value: string;
  tone: "blue" | "green" | "amber";
}) {
  const dotClass = tone === "green" ? "bg-emerald-500" : tone === "amber" ? "bg-wait" : "bg-action";
  return (
    <div className="flex items-center gap-2">
      <span className="font-semibold text-ink">{label}</span>
      <span className={`h-2 w-2 rounded-full ${dotClass}`} />
      <span>{value}</span>
    </div>
  );
}

function MerchantBlockerRow({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <AlertTriangle aria-hidden="true" className="mt-0.5 shrink-0 text-risk" size={16} />
      <div>
        <div className="text-sm font-semibold text-ink">{title}</div>
        <div className="mt-0.5 text-sm leading-5 text-slate-600">{detail}</div>
      </div>
    </div>
  );
}

function MerchantQueuePreview({ data }: { data: MerchantDiagnosticsResponse }) {
  const rows = data.decision_queue.slice(0, 6);
  if (rows.length === 0) {
    return (
      <section id="merchant-queue" className="mb-6 rounded-md border border-line bg-white p-4">
        <BlockerNotice message="Brak kolejki Merchant. Najpierw uruchom odczyt danych Merchant." />
      </section>
    );
  }
  return (
    <section id="merchant-queue" className="mb-6 overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="flex min-h-12 items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold text-ink">Kolejka problemów produktów</h2>
        <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
          {data.decision_queue.length} decyzji
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold text-slate-600">
            <tr>
              <th className="px-4 py-3">Priorytet</th>
              <th className="px-4 py-3">Problem</th>
              <th className="px-4 py-3">Dowody</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Następny krok</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((decision) => (
              <tr key={decision.id} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-4 py-3">
                  <span className="rounded border border-risk/30 bg-risk/10 px-2 py-1 text-xs font-semibold text-risk">
                    {decision.priority_label}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-ink">{decision.title}</div>
                  <div className="mt-1 text-xs leading-5 text-slate-600">
                    {merchantDecisionShortContext(decision)}
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-700">{decision.evidence_summary_label}</td>
                <td className="px-4 py-3">
                  <StatusBadge value={decision.status} label={decision.status_label} />
                </td>
                <td className="px-4 py-3 text-slate-700">
                  {decision.action_ids[0] ? (
                    <a className="font-medium text-action hover:underline" href={`/actions/${decision.action_ids[0]}`}>
                      Przejdź do review
                    </a>
                  ) : (
                    decision.next_step
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function primaryMerchantDecision(data: MerchantDiagnosticsResponse) {
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  return (
    data.operator_summary.top_decision_ids
      .map((decisionId) => decisionsById.get(decisionId))
      .find((decision): decision is MerchantDecisionItem => Boolean(decision)) ??
    data.decision_queue[0]
  );
}

function merchantDecisionShortContext(decision: MerchantDecisionItem) {
  return [
    decision.issue_type_label ?? decision.decision_type_label,
    decision.affected_attribute_label ? `atrybut: ${decision.affected_attribute_label}` : null,
    decision.product_count ? `produkty/zgłoszenia: ${decision.product_count}` : null,
    decision.sample_titles.length ? `próbki: ${decision.sample_titles.slice(0, 2).join(", ")}` : null
  ].filter((value): value is string => Boolean(value)).join(" · ");
}

function formatMerchantValue(value: number | string) {
  if (typeof value === "number") {
    return new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 0 }).format(value);
  }
  return value;
}

function MerchantExpandableReviewPanel({ data }: { data: MerchantDiagnosticsResponse }) {
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
            powiązanie produktów z Ads/GA4, ograniczenia i dowody w WILQ.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
          <MetricTile label="Zgłoszenia" value={data.operator_summary.reported_issue_occurrences} />
          <MetricTile label="Dowody" value={data.evidence_summary_label} />
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

function MerchantExpandableActionsPanel({
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

function MerchantFeedSafetyPanel({ data }: { data: MerchantDiagnosticsResponse }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa pliku produktowego
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Merchant Center pozostaje w trybie przeglądu i przygotowania. WILQ może pokazać
              kolejkę problemów, dowody i podgląd zmian, ale nie może zmienić pliku produktowego,
              obiecać ponownego zatwierdzenia produktu ani zapisać zmiany bez sprawdzenia w WILQ i audytu.
            </p>
          </div>
        </div>
        <TraceLine
          label="Nie wolno twierdzić"
          values={data.sections.flatMap((section) => section.blocked_claim_labels)}
        />
      </section>
  );
}

function MerchantSelectedDecisionPanel({ data }: { data: MerchantDiagnosticsResponse }) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const primaryDecision =
    summary.top_decision_ids
      .map((decisionId) => decisionsById.get(decisionId))
      .find((decision): decision is MerchantDecisionItem => Boolean(decision)) ??
    data.decision_queue[0];
  if (!primaryDecision) {
    return (
      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <BlockerNotice message="Brak decyzji Merchant w WILQ. Nie pokazujemy rekomendacji pliku produktowego bez kolejki decyzji." />
      </section>
    );
  }

  const primaryPreviewCard = primaryDecision.preview_cards[0];
  const requiredValidationSummary = primaryPreviewCard?.rows.find(
    (row) => row.label === "Warunki sprawdzenia"
  )?.value;
  const workSteps = [
    "Najpierw sprawdź powiązanie produktu albo największy problem atrybutu w kolejce Merchant.",
    "Potem przygotuj podgląd zmian przez akcję do sprawdzenia, bez zapisu do pliku produktowego.",
    "Nie obiecuj ponownego zatwierdzenia, odzyskanego przychodu, ROAS produktu ani wpływu ceny bez brakujących kontraktów."
  ];
  const blockedClaimLabels = uniqueValues([
    ...summary.blocked_claim_labels,
    ...primaryDecision.blocked_claim_labels
  ]).slice(0, 6);
  const measurementPlan = merchantMerchantMeasurementPlan(primaryDecision);
  const reportedIssueCount =
    primaryDecision.issue_count ??
    merchantMetricTileValue(primaryDecision, "raporty razem") ??
    primaryDecision.product_count ??
    "licznik niepotwierdzony";
  const maxReportCount =
    primaryDecision.product_count ??
    merchantMetricTileValue(primaryDecision, "max zgłoszeń") ??
    "licznik niepotwierdzony";
  const contextCount =
    merchantMetricTileValue(primaryDecision, "konteksty") ??
    (primaryDecision.issue_cluster_ids.length || null) ??
    "zakres niepotwierdzony";

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Merchant: co dziś zrobić
          </div>
          <h2 className="mt-1 text-lg font-semibold tracking-normal">{summary.title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {primaryDecision.title}. To jest skrót pierwszej decyzji z kolejki Merchant:
            najpierw ręczny przegląd problemu, potem podgląd zmian i dopiero później
            ewentualna sprawdzona zmiana. Pełne warunki i dowody zostają niżej.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
          <MetricTile label="Wszystkie zgłoszenia" value={summary.reported_issue_occurrences} />
          <MetricTile label="Raporty tej decyzji" value={reportedIssueCount} />
          <MetricTile label="Najwięcej w raporcie" value={maxReportCount} />
          <MetricTile label="Konteksty" value={contextCount} />
        </div>
      </div>

      <div className="mb-4 grid gap-3 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Kolejność pracy</h3>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-6 text-slate-700">
            {workSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>

        <div className="rounded-md border border-risk/25 bg-risk/10 p-3">
          <h3 className="text-sm font-semibold text-ink">Czego nie obiecywać</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            To jest kolejka przeglądu pliku produktowego, nie dowód efektu biznesowego ani zapis zmian.
          </p>
          <TraceLine label="Nie wolno obiecać" values={blockedClaimLabels} />
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Dlaczego to ma znaczenie</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            WILQ zgrupował ten problem jako jedną decyzję operatorską, żeby marketer
            nie przeglądał osobno powtarzalnych raportów Merchant. Najpierw sprawdzamy
            typ problemu, atrybut, kraj i kontekst raportowania.
          </p>
          <TraceLine
            label="Zakres"
            values={[
              primaryDecision.issue_type_label,
              primaryDecision.affected_attribute_label,
              primaryDecision.country
            ].filter((value): value is string => Boolean(value))}
            empty="WILQ nie podał pełnego zakresu problemu; sprawdź typ, atrybut i kraj przed decyzją."
          />
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny następny krok</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Otwórz akcję do sprawdzenia, sprawdź dowody i przygotuj podgląd zmian.
            Bez potwierdzenia operatora WILQ nie zmienia pliku produktowego ani danych produktu.
          </p>
          <TraceLine
            label="Akcje"
            values={[primaryDecision.action_summary_label]}
            empty="WILQ nie podał akcji; zostaje ręczny przegląd Merchant."
          />
          {primaryDecision.action_ids[0] ? (
            <a
              href={`/actions/${primaryDecision.action_ids[0]}`}
              className="mt-3 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
            >
              Przejdź do sprawdzenia
            </a>
          ) : null}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Co oznaczają liczby</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Zgłoszenia w raportach nie są liczbą unikalnych produktów ani SKU. Ten panel
            pokazuje kolejkę sprawdzenia Merchant, a nie gotową listę zmian w pliku produktowym.
          </p>
          <TraceLine
            label="Źródło decyzji"
            values={[summary.decision_source_label, summary.drilldown_source_label]}
            empty="WILQ nie podał źródła decyzji; nie traktuj liczników jako rekomendacji."
          />
          <TraceLine label="Znaczenie liczników" values={[summary.count_semantics_label]} />
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Dowody i źródła</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Decyzja pochodzi z aktualnych danych WILQ i jest oparta o dowody Merchant,
            nie o ręczny opis ani screenshot.
          </p>
          <TraceLine
            label="Źródła"
            values={primaryDecision.source_connector_labels}
            empty="WILQ nie podał źródeł danych; nie oceniaj pliku bez odczytu."
          />
          <TraceLine
            label="Dowody"
            values={primaryDecision.evidence_summary_label ? [primaryDecision.evidence_summary_label] : []}
            empty="WILQ nie podał dowodów źródłowych; nie traktuj tego jako rekomendacji."
          />
          {data.latest_refresh ? (
            <TraceLine
              label="Ostatni odczyt"
              values={data.latest_refresh_status_label ? [data.latest_refresh_status_label] : []}
            />
          ) : null}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Czego WILQ nie zrobi teraz</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Nie ma zapisu do pliku produktowego ani automatycznej naprawy zatwierdzenia produktu.
            Najpierw ręczny przegląd, podgląd zmian, zgoda operatora i audyt.
          </p>
          <TraceLine
            label="Nie wolno twierdzić"
            values={uniqueValues([
              ...summary.blocked_claim_labels,
              ...primaryDecision.blocked_claim_labels
            ])}
          />
          <TraceLine
            label="Brakujące wejścia"
            values={requiredValidationSummary ? [requiredValidationSummary] : []}
            empty="WILQ nie zgłosił brakujących wejść dla tego przeglądu."
          />
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Jak później sprawdzimy efekt</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">{measurementPlan}</p>
          <TraceLine
            label="Warunki pomiaru"
            values={[
              "ponowny odczyt Merchant",
              "audyt zmiany",
              "porównanie statusów problemu",
              "brak obietnic przychodu albo zwrotu z reklam bez danych po zmianie"
            ]}
          />
        </div>
      </div>
    </section>
  );
}

function merchantMetricTileValue(decision: MerchantDecisionItem, key: string) {
  const value = decision.metric_tiles?.[key];
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) return value;
  return null;
}

function merchantMerchantMeasurementPlan(decision: MerchantDecisionItem) {
  if (decision.decision_type === "review_product_state_mapping") {
    return "Po ręcznym przeglądzie porównamy kolejne odczyty Merchant i stan produktów w Ads dla tych samych produktów. Bez pełnego okna po zmianie WILQ nie będzie obiecywał zwrotu z reklam, przychodu ani wpływu naprawy.";
  }
  if (decision.decision_type === "review_feed_status") {
    return "Po zatwierdzonym działaniu sprawdzimy kolejny odczyt Merchant: status pliku produktowego, liczbę zgłoszeń i czy problem nadal występuje w tych samych kontekstach raportowania.";
  }
  return "Po ręcznym przeglądzie i ewentualnie zatwierdzonym podglądzie zmian sprawdzimy kolejny odczyt Merchant: czy ten sam typ problemu, atrybut i kontekst raportowania nadal występują. Nie obiecujemy odzyskanego zatwierdzenia ani wpływu na przychód bez audytu i danych po zmianie.";
}

function MerchantOperatorSummary({ data }: { data: MerchantDiagnosticsResponse }) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const clustersById = new Map(data.issue_clusters.map((cluster) => [cluster.id, cluster]));
  const itemsById = new Map(
    data.sections.flatMap((section) => section.tactical_items).map((item) => [item.id, item])
  );
  const topDecisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is MerchantDecisionItem => Boolean(decision));
  const topIssueClusters = summary.top_issue_cluster_ids
    .map((clusterId) => clustersById.get(clusterId))
    .filter((cluster): cluster is MerchantDiagnosticsResponse["issue_clusters"][number] =>
      Boolean(cluster)
    );
  const topIssueItems = summary.top_tactical_item_ids
    .map((itemId) => itemsById.get(itemId))
    .filter((item): item is MerchantDiagnosticsResponse["sections"][number]["tactical_items"][number] =>
      Boolean(item)
    );
  const actionIds = summary.action_ids;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Przegląd Merchant
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            {summary.title}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {summary.summary}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Produkty" value={data.product_count ?? 0} />
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
          <MetricTile label="Zgłoszenia" value={summary.reported_issue_occurrences} />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {topDecisions.length > 0 ? (
            topDecisions.map((decision) => (
              <MerchantDecisionCard key={decision.id} decision={decision} />
            ))
          ) : topIssueClusters.length > 0 ? (
            topIssueClusters.map((cluster) => (
              <article key={cluster.id} className="rounded-md border border-line bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">
                      {cluster.issue_type_label ?? "problem pliku produktowego"}
                      {cluster.affected_attribute_label
                        ? `; atrybut: ${cluster.affected_attribute_label}`
                        : ""}
                      {`; kontekst: ${cluster.reporting_context_label}`}
                    </h3>
                    <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                      {cluster.severity_label ?? "status nieznany"}.{" "}
                      {cluster.resolution_label ?? "ścieżka rozwiązania niepotwierdzona w Merchant"}.
                    </p>
                  </div>
                  <StatusBadge value={cluster.risk} label={cluster.risk_label} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  Raport pokazuje {cluster.reported_issue_summary_label}
                  {cluster.country ? ` w kraju ${cluster.country}` : ""}
                  {`; kontekst: ${cluster.reporting_context_label}`}.
                </p>
                {cluster.sample_unavailable_reason ? (
                  <p className="mt-2 text-xs leading-5 text-slate-600">
                    {cluster.sample_unavailable_reason}
                  </p>
                ) : null}
                <p className="mt-2 text-sm font-medium text-ink">{cluster.next_step}</p>
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
                  <span className="rounded border border-line bg-white px-2 py-1">
                    zgłoszenia: {cluster.product_count}
                  </span>
                  {cluster.country ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      kraj: {cluster.country}
                    </span>
                  ) : null}
                  <span className="rounded border border-line bg-white px-2 py-1">
                    kontekst: {cluster.reporting_context_label}
                  </span>
                  {cluster.resolution ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      rozwiązanie:{" "}
                      {cluster.resolution_label ?? "ścieżka rozwiązania niepotwierdzona w Merchant"}
                    </span>
                  ) : null}
                  {cluster.action_id ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      akcja do sprawdzenia
                    </span>
                  ) : null}
                </div>
              </article>
            ))
          ) : topIssueItems.length > 0 ? (
            topIssueItems.map((item) => (
              <article key={item.id} className="rounded-md border border-line bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                    <LabelChipRow
                      className="mt-2"
                      chips={[
                        { label: "Zadanie", value: item.intent_label },
                        { label: "Priorytet", value: item.priority_label }
                      ]}
                    />
                  </div>
                  <StatusBadge value={item.risk} label={item.risk_label} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{item.diagnosis}</p>
                <p className="mt-2 text-sm font-medium text-ink">{item.next_step}</p>
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
                  {tacticalContextPairs(item).map(({ key, label, valueLabel }) => (
                    <span key={key} className="rounded border border-line bg-white px-2 py-1">
                      {label}: {valueLabel}
                    </span>
                  ))}
                </div>
              </article>
            ))
          ) : (
            <BlockerNotice message="Brak kolejki Merchant. Najpierw uruchom odczyt danych Merchant." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb pracy</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine
              label="Typy problemów"
              values={summary.issue_types}
              empty="WILQ nie podał typów problemów; zacznij od odczytu Merchant."
            />
            <TraceLine
              label="Dowody"
              values={summary.evidence_summary_label ? [summary.evidence_summary_label] : []}
              empty="WILQ nie podał dowodów źródłowych; nie traktuj trybu pracy jako rekomendacji."
            />
            <TraceLine
              label="Akcje"
              values={[summary.action_summary_label]}
              empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczna ocena."
            />
            <TraceLine
              label="Nie wolno twierdzić"
              values={summary.blocked_claim_labels}
            />
          </div>
          {actionIds.length > 0 ? (
            <a
              href={`/actions/${actionIds[0]}`}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
            >
              Sprawdź w WILQ
            </a>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function MerchantUnknowns({ data }: { data: MerchantDiagnosticsResponse }) {
  if (data.unknowns.length === 0) return null;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Czego nie wiemy o pliku produktowym Merchant Center
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Te ograniczenia blokują zbyt mocne wnioski i automatyczne zmiany pliku produktowego.
            Kolejka decyzji jest źródłem decyzji, a grupy problemów są szczegółowym
            przeglądem.
          </p>
        </div>
        <MetricTile label="Ograniczenia" value={data.unknowns.length} />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {data.unknowns.map((unknown) => (
          <article key={unknown.id} className="rounded-md border border-line bg-slate-50 p-3">
            <h3 className="text-sm font-semibold text-ink">{unknown.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">{unknown.reason}</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">{unknown.impact}</p>
            <p className="mt-2 text-sm font-medium text-ink">{unknown.next_step}</p>
            <div className="mt-2 text-xs text-slate-600">
              <TraceLine
                label="Nie wolno twierdzić"
                values={unknown.blocked_claim_labels}
              />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function MerchantProductSampleReadiness({ data }: { data: MerchantDiagnosticsResponse }) {
  const readiness = data.product_sample_readiness;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Gotowość próbek produktów
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {readiness.summary}
          </p>
          <p className="mt-2 text-sm font-medium text-ink">
            {readiness.next_step}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs">
          <MetricTile label="Status" value={readiness.status_label} />
          <MetricTile label="Próbki" value={readiness.sample_count} />
        </div>
      </div>
      <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine label="Stan danych" values={[readiness.summary, readiness.next_step]} />
        <TraceLine
          label="Przykładowe produkty"
          values={[
            readiness.sample_summary_label ||
              "WILQ nie podał próbek produktów; sprawdź Merchant przed edycją"
          ]}
        />
        <TraceLine
          label="Przykładowe tytuły"
          values={
            readiness.sample_title_labels.length
              ? readiness.sample_title_labels
              : ["WILQ nie podał tytułów próbek; identyfikuj produkt w Merchant przed oceną"]
          }
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={readiness.blocked_claim_labels}
        />
      </div>
    </section>
  );
}

function MerchantProductPerformanceReadiness({ data }: { data: MerchantDiagnosticsResponse }) {
  const readiness = data.product_performance_readiness;
  const visibleRows = readiness.performance_rows.slice(0, 4);
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Produkty połączone z Ads/GA4
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {readiness.summary}
          </p>
          <p className="mt-2 text-sm font-medium text-ink">
            {readiness.next_step}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Status" value={readiness.status_label} />
          <MetricTile label="Połączone produkty" value={readiness.joined_product_count} />
          <MetricTile label="Próbki" value={readiness.merchant_sample_count} />
        </div>
      </div>
      <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine label="Stan danych" values={[readiness.summary, readiness.next_step]} />
        <TraceLine
          label="Źródła"
          values={readiness.source_connector_labels}
          empty="WILQ nie podał źródeł danych; nie łącz Merchant z Ads/GA4 bez odczytu."
        />
        <TraceLine
          label="Dowody"
          values={readiness.evidence_summary_label ? [readiness.evidence_summary_label] : []}
          empty="WILQ nie podał dowodów źródłowych; nie oceniaj gotowości połączenia."
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={readiness.blocked_claim_labels}
        />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
        <MetricTile label="Fakty Ads" value={readiness.ads_product_fact_count} />
        <MetricTile label="Fakty GA4" value={readiness.ga4_product_fact_count} />
        <MetricTile label="Próbki produktów" value={readiness.sample_product_summary_label} />
        <MetricTile label="Wiersze" value={readiness.performance_rows.length} />
      </div>
      {visibleRows.length > 0 ? (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {visibleRows.map((row) => (
            <MerchantProductPerformanceRowCard key={row.product_id} row={row} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

function MerchantProductPerformanceRowCard({
  row
}: {
  row: MerchantProductPerformanceRow;
}) {
  const title = row.title_label || "Produkt Merchant do sprawdzenia";
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-1 text-xs text-slate-500">{row.product_reference_label}</p>
      <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs">
        <MetricTile label="Status Ads" value={row.ads_product_status_label} />
        <MetricTile label="Dostępność Ads" value={row.ads_product_availability_label} />
        <MetricTile label="Cena Ads" value={row.ads_product_price_label} />
        <MetricTile label="Kliknięcia Ads" value={row.ads_clicks_label} />
        <MetricTile label="Koszt Ads" value={row.ads_cost_label} />
        <MetricTile label="Zakupy GA4" value={row.ga4_ecommerce_purchases_label} />
        <MetricTile label="Przychód GA4" value={row.ga4_purchase_revenue_label} />
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Problem Merchant"
          values={[
            row.issue_type_label,
            row.affected_attribute_label,
            row.country,
            row.reporting_context_label
          ].filter((value): value is string => Boolean(value))}
          empty="WILQ nie podał kontekstu problemu; nie edytuj produktu bez sprawdzenia."
        />
        <TraceLine
          label="Źródła"
          values={row.source_connector_labels}
          empty="WILQ nie podał źródeł danych; nie oceniaj wiersza bez odczytu Merchant."
        />
        <TraceLine
          label="Dowody"
          values={row.evidence_summary_label ? [row.evidence_summary_label] : []}
          empty="WILQ nie podał dowodów źródłowych; nie traktuj wiersza jako rekomendacji."
        />
        <TraceLine
          label="Brakujące metryki"
          values={row.missing_metric_labels}
          empty="metryki kompletne"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={row.blocked_claim_labels}
        />
      </div>
    </article>
  );
}

function MerchantPriceImpactReadiness({ data }: { data: MerchantDiagnosticsResponse }) {
  const readiness = data.price_impact_readiness;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Wpływ ceny produktu
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {readiness.summary}
          </p>
          <p className="mt-2 text-sm font-medium text-ink">{readiness.next_step}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-5">
          <MetricTile label="Status" value={readiness.status_label} />
          <MetricTile label="Ceny teraz" value={readiness.products_with_current_price} />
          <MetricTile label="Historia cen" value={readiness.products_with_previous_price} />
          <MetricTile label="Zmiany ceny" value={readiness.products_with_price_change} />
          <MetricTile
            label="Bez zmiany"
            value={readiness.products_with_unchanged_price_history}
          />
        </div>
      </div>
      <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine label="Stan danych" values={[readiness.summary, readiness.next_step]} />
        <TraceLine
          label="Źródła"
          values={readiness.source_connector_labels}
          empty="WILQ nie podał źródeł danych; nie oceniaj wpływu ceny bez odczytu."
        />
        <TraceLine
          label="Dowody"
          values={readiness.evidence_summary_label ? [readiness.evidence_summary_label] : []}
          empty="WILQ nie podał dowodów źródłowych; nie oceniaj wpływu ceny jako pewnego."
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={readiness.blocked_claim_labels}
        />
      </div>
      {readiness.preview_cards.length > 0 ? (
        <div className="mt-3 grid gap-2">
          {readiness.preview_cards.map((card) => (
            <ActionPreviewCard key={card.id} card={card} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

function MerchantDecisionCard({ decision }: { decision: MerchantDecisionItem }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{decision.title}</h3>
          <LabelChipRow
            className="mt-1"
            chips={[
              { label: "Typ", value: decision.decision_type_label },
              { label: "Priorytet", value: decision.priority_label }
            ]}
          />
        </div>
        <StatusBadge value={decision.risk} label={decision.risk_label} />
      </div>
      {decision.summary ? (
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {decision.summary}
        </p>
      ) : null}
      <p className="mt-2 text-sm leading-6 text-slate-700">
        {decision.rationale}
      </p>
      <p className="mt-2 text-sm font-medium text-ink">
        {decision.next_step}
      </p>
      {Object.keys(decision.metric_tiles ?? {}).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
        {decision.issue_type ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            problem: {decision.issue_type_label ?? "problem pliku produktowego"}
          </span>
        ) : null}
        {decision.affected_attribute ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            atrybut: {decision.affected_attribute_label ?? "atrybut"}
          </span>
        ) : null}
        {decision.country ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            kraj: {decision.country}
          </span>
        ) : null}
        {decision.reporting_context_label ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            kontekst: {decision.reporting_context_label}
          </span>
        ) : null}
      </div>
      <div className="mt-2 grid gap-1.5 text-xs text-slate-600">
        {decision.sample_product_ids.length || decision.sample_titles.length ? (
          <div className="rounded border border-line bg-white p-2">
            <p className="font-medium text-ink">Przykładowe produkty do sprawdzenia</p>
            <TraceLine label="Próbki" values={["przykłady dostępne w pełnym przeglądzie"]} />
            <TraceLine
              label="Tytuły"
              values={decision.sample_titles.slice(0, 4)}
              empty="WILQ nie podał tytułów próbek; identyfikuj produkt w Merchant przed oceną."
            />
            <p className="mt-1 text-xs text-slate-500">
              To są przykłady z odczytu Merchant, nie pełna lista SKU ani gotowa zmiana pliku produktowego.
            </p>
          </div>
        ) : null}
        {decision.preview_cards.length > 0 ? (
          <div className="grid gap-2">
            {decision.preview_cards.map((card) => (
              <ActionPreviewCard key={card.id} card={card} />
            ))}
          </div>
        ) : null}
        <TraceLine
          label="Dowody"
          values={decision.evidence_summary_label ? [decision.evidence_summary_label] : []}
          empty="WILQ nie podał dowodów źródłowych; nie traktuj tej decyzji jako rekomendacji."
        />
        <TraceLine
          label="Akcje"
          values={[decision.action_summary_label]}
          empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczny przegląd."
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={decision.blocked_claim_labels}
        />
      </div>
    </article>
  );
}

function MerchantDiagnosticProof({ data }: { data: MerchantDiagnosticsResponse }) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  const visibleMetricFacts = metricFacts.slice(0, 4);
  const blockedClaims = data.sections.flatMap((section) => section.blocked_claim_labels);
  const sectionTitles = data.sections.map((section) => section.label);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i warunki przeglądu Merchant
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót źródeł danych i blokad w WILQ. Pełna kolejka pracy
            jest powyżej; tutaj widać, z jakich sekcji i dowodów wynika przegląd.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Obszary danych" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Dowody" value={data.evidence_summary_label} />
        </div>
      </div>
      {visibleMetricFacts.length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          {visibleMetricFacts.map((fact, index) => (
            <MetricTile
              key={`${fact.source_connector}-${fact.name}-${fact.evidence_id}-${index}`}
              label={fact.metric_label || "Metryka bez etykiety"}
              value={fact.value}
            />
          ))}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={sectionTitles} />
        <TraceLine label="Źródła danych" values={data.source_connector_labels} />
        <TraceLine
          label="Akcje"
          values={[data.action_summary_label]}
          empty="WILQ nie podał akcji; panel zostaje tylko podsumowaniem dowodów."
        />
        <TraceLine label="Nie wolno twierdzić" values={blockedClaims} />
      </div>
    </section>
  );
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
