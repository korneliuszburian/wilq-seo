import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  CircleSlash,
  Gauge,
  LineChart,
  Megaphone,
  MousePointerClick,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Target
} from "lucide-react";

import {
  ActionObject,
  AdsDiagnosticsResponse,
  DemandGenReadinessContract,
  Ga4DiagnosticsResponse,
  getActions,
  getAdsDiagnosticsSummary,
  getDemandGenDiagnostics,
  getGa4Diagnostics
} from "../lib/api";
import { BlockerNotice } from "../components/OperatorPrimitives";
import {
  CompactStatTile,
  DashboardToolbar,
  DenseQueueTable,
  ForbiddenClaimsStrip,
  PriorityBadge,
  RiskPill,
  SourceFreshnessStrip,
  StatusPill
} from "../components/DashboardMockupPrimitives";

type AdsDecision = AdsDiagnosticsResponse["decision_queue"][number];

export function AdsDoctorSurface() {
  const diagnostics = useQuery({
    queryKey: ["ads-diagnostics", "summary"],
    queryFn: getAdsDiagnosticsSummary
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });
  const ga4 = useQuery({
    queryKey: ["ga4-diagnostics"],
    queryFn: getGa4Diagnostics
  });
  const demandGen = useQuery({
    queryKey: ["demand-gen-diagnostics"],
    queryFn: getDemandGenDiagnostics
  });

  if (diagnostics.isLoading) {
    return <AdsDiagnosticsLoadingState />;
  }

  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać danych Ads. WILQ nie może udawać diagnozy bez danych." />
      </main>
    );
  }

  const data = diagnostics.data;
  const summary = data.operator_summary;
  const actionsPending = actions.isLoading;
  const routeActions = (actions.data ?? []).filter((action) => data.action_ids.includes(action.id));
  const ga4Data = ga4.isLoading || ga4.error ? null : ga4.data ?? null;
  const demandGenData = demandGen.isLoading || demandGen.error ? null : demandGen.data ?? null;
  const primaryDecision = pickPrimaryDecision(data);
  const blockedDecisionCount = data.decision_queue.filter(
    (decision) => decision.status === "blocked"
  ).length;
  const measurementBlockers =
    (ga4Data?.operator_summary.measurement_issue_count ?? 0) +
    (ga4Data?.decision_blocker_count ?? 0);
  const blockedClaims = uniqueLabels([
    ...summary.top_blocked_claim_labels,
    ...summary.blocked_claim_labels,
    ...(ga4Data?.operator_summary.blocked_claim_labels ?? []),
    ...(demandGenData?.blocked_claims ?? [])
  ]).slice(0, 6);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <DashboardToolbar
        title="Reklamy i pomiar"
        description="Tu sprawdzasz Ads, GA4 i Demand Gen bez skracania bramek pomiaru. WILQ pokazuje tylko to, co wynika z aktualnych dowodów."
        dateLabel={dateLabel(data.generated_at ?? ga4Data?.generated_at)}
      />

      <section className="mb-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <CompactStatTile
          value={data.decision_queue.length}
          label="decyzji Ads"
          actionLabel={summary.action_summary_label}
          tone="blue"
          icon={<Megaphone aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={measurementBlockers}
          label="blokady pomiaru"
          actionLabel={ga4Data?.conversion_readiness_contract.status_label ?? "GA4 do sprawdzenia"}
          tone={measurementBlockers > 0 ? "red" : "green"}
          icon={<Gauge aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={actionsPending ? "…" : routeActions.length}
          label="bezpieczne akcje"
          actionLabel={actionsPending ? "wczytuję kolejkę akcji" : data.action_summary_label}
          tone="amber"
          icon={<CheckCircle2 aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={data.evidence_summary_label}
          label="dowody źródłowe"
          actionLabel={data.live_data_status_label}
          tone="purple"
          icon={<BarChart3 aria-hidden="true" size={22} />}
        />
      </section>

      <SourceFreshnessStrip
        items={[
          {
            label: "Google Ads",
            detail: data.freshness_assessment.state_label || data.connector_status_label,
            tone: data.freshness_assessment.requires_refresh ? "amber" : "green",
            icon: <RefreshCw aria-hidden="true" size={16} />
          },
          {
            label: "GA4",
            detail: ga4Data?.freshness_assessment.state_label ?? "nieodczytane",
            tone: ga4Data ? (ga4Data.freshness_assessment.requires_refresh ? "amber" : "green") : "red",
            icon: <LineChart aria-hidden="true" size={16} />
          },
          {
            label: "Demand Gen",
            detail: demandGenData?.status === "blocked" ? "blokada" : demandGenData?.status ?? "nieodczytane",
            tone: demandGenData?.status === "blocked" || !demandGenData ? "red" : "green",
            icon: <Sparkles aria-hidden="true" size={16} />
          },
          {
            label: "ActionObject",
            detail: actionsPending ? "wczytuję kolejkę akcji" : data.action_summary_label,
            tone: actionsPending ? "amber" : routeActions.length > 0 ? "blue" : "neutral",
            icon: <ShieldAlert aria-hidden="true" size={16} />
          }
        ]}
      />

      <MeasurementFirstBanner
        data={data}
        ga4Data={ga4Data}
        demandGenData={demandGenData}
      />

      <section className="mb-5 grid gap-5 xl:grid-cols-[1.45fr_1fr]">
        <DenseQueueTable
          title="Kolejka diagnostyczna"
          rows={data.decision_queue.slice(0, 6)}
          selectedRowKey={primaryDecision?.id}
          getRowKey={(decision) => decision.id}
          columns={[
            {
              key: "priority",
              header: "Priorytet",
              render: (decision) => <PriorityBadge value={priorityFromDecision(decision)} />
            },
            {
              key: "topic",
              header: "Temat",
              render: (decision) => (
                <div className="max-w-md">
                  <div className="font-semibold text-ink">{decision.title}</div>
                  <div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-600">
                    {decision.start_here_summary || decision.summary}
                  </div>
                </div>
              )
            },
            {
              key: "proof",
              header: "Dowody",
              render: (decision) => (
                <div className="grid gap-1 text-xs text-slate-600">
                  <span>{decision.evidence_summary_label}</span>
                  <span>{decision.action_summary_label || "bez akcji"}</span>
                </div>
              )
            },
            {
              key: "status",
              header: "Status",
              render: (decision) => (
                <RiskPill
                  label={decision.status_label || decision.risk_label || decision.status}
                  risk={decision.status === "blocked" ? "blocked" : riskFromDecision(decision.risk)}
                />
              )
            },
            {
              key: "next",
              header: "Następny krok",
              render: (decision) => (
                <span className="text-sm leading-5 text-slate-700">{decision.next_step}</span>
              )
            }
          ]}
          action={<StatusPill label={`${blockedDecisionCount} blokady`} tone={blockedDecisionCount > 0 ? "red" : "green"} />}
        />

        <SafeWorkModes
          data={data}
          ga4Data={ga4Data}
          demandGenData={demandGenData}
          actions={routeActions}
          actionsPending={actionsPending}
        />
      </section>

      <section className="mb-5 grid gap-4 lg:grid-cols-3">
        <CompactDiagnosticCard
          icon={<Megaphone aria-hidden="true" size={18} />}
          title="Ads"
          statusLabel={data.connector_status_label}
          summary={summary.summary}
          facts={[
            `${summary.campaign_count} kampanii`,
            `${summary.search_term_count} zapytań`,
            formatCost(summary.total_cost_micros, data.account_currency_read_contract.currency_code)
          ]}
          nextStep={summary.next_step}
          tone="blue"
        />
        <CompactDiagnosticCard
          icon={<LineChart aria-hidden="true" size={18} />}
          title="GA4"
          statusLabel={ga4Data?.conversion_readiness_contract.status_label ?? "brak odczytu GA4"}
          summary={
            ga4Data?.operator_summary.summary ??
            "WILQ nie może dołożyć warstwy pomiaru GA4 do tego widoku, dopóki endpoint GA4 nie odpowie."
          }
          facts={[
            `${ga4Data?.operator_summary.measurement_issue_count ?? 0} problemy pomiaru`,
            ga4Data?.evidence_summary_label ?? "brak dowodów GA4",
            ga4Data?.action_summary_label ?? "brak akcji GA4"
          ]}
          nextStep={ga4Data?.operator_summary.next_step ?? "Sprawdź /ga4 albo status WILQ przed wnioskiem o konwersjach."}
          tone="red"
        />
        <CompactDiagnosticCard
          icon={<Sparkles aria-hidden="true" size={18} />}
          title="Demand Gen"
          statusLabel={demandGenData?.title ?? "brak odczytu Demand Gen"}
          summary={
            demandGenData?.summary ??
            "WILQ nie ma odczytu Demand Gen w tym widoku, więc nie pokaże rekomendacji trybu kampanii."
          }
          facts={[
            metricTileValue(demandGenData, "kampanie Demand Gen"),
            metricTileValue(demandGenData, "reklamy Demand Gen"),
            demandGenData?.evidence_summary_label ?? "brak dowodów Demand Gen"
          ]}
          nextStep={demandGenData?.next_step ?? "Nie rekomenduj Demand Gen bez kontraktu gotowości."}
          tone="purple"
        />
      </section>

      <ForbiddenClaimsStrip
        claims={
          blockedClaims.length > 0
            ? blockedClaims
            : [
                "werdykt zwrotu z reklam",
                "twierdzenie o przychodzie",
                "werdykt marnowania budżetu",
                "zmiana kampanii bez ActionObject"
              ]
        }
      />
    </main>
  );
}

function AdsDiagnosticsLoadingState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <DashboardToolbar
        title="Reklamy i pomiar"
        description="WILQ pobiera źródłowe dane Ads. Nie pokazuję rekomendacji, dopóki odczyt nie wróci."
        dateLabel="Dzisiaj"
      />
      <section className="rounded-md border border-amber-200 bg-amber-50 p-5 shadow-sm">
        <div className="text-sm font-semibold text-amber-900">Odczyt Ads w toku</div>
        <p className="mt-2 text-sm leading-6 text-amber-800">
          Zapis zmian i wnioski o ROAS, przychodzie, waste oraz konwersjach pozostają zablokowane
          do czasu potwierdzenia danych.
        </p>
      </section>
    </main>
  );
}

function MeasurementFirstBanner({
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

function SafeWorkModes({
  data,
  ga4Data,
  demandGenData,
  actions,
  actionsPending
}: {
  data: AdsDiagnosticsResponse;
  ga4Data: Ga4DiagnosticsResponse | null;
  demandGenData: DemandGenReadinessContract | null;
  actions: ActionObject[];
  actionsPending: boolean;
}) {
  const summary = data.operator_summary;

  return (
    <section className="overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold text-ink">Bezpieczne tryby pracy</h2>
        <p className="mt-1 text-sm leading-5 text-slate-600">
          WILQ pokazuje review i podglądy. Nie zapisuje zmian w Ads ani nie odblokowuje obietnic bez bramek.
        </p>
      </div>
      <div className="divide-y divide-line">
        <ModeRow
          icon={<MousePointerClick aria-hidden="true" size={16} />}
          title="Review Ads"
          detail={`${summary.ready_area_count} gotowe obszary, ${summary.blocked_area_count} blokady`}
          statusLabel={summary.operator_review_gate_summary_label || "wymaga review"}
          href="/actions"
        />
        <ModeRow
          icon={<Gauge aria-hidden="true" size={16} />}
          title="Sprawdź pomiar GA4"
          detail={ga4Data?.freshness_assessment.next_step ?? "Brak odczytu GA4 w tym widoku"}
          statusLabel={ga4Data?.action_summary_label ?? "sprawdź GA4"}
          href="/ga4"
        />
        <ModeRow
          icon={<Sparkles aria-hidden="true" size={16} />}
          title="Demand Gen tylko do gotowości"
          detail={demandGenData?.next_step ?? "Brak kontraktu Demand Gen"}
          statusLabel={demandGenData?.action_summary_label ?? "review-only"}
          href="/ads-doctor/demand-gen"
        />
        <ModeRow
          icon={<Target aria-hidden="true" size={16} />}
          title="ActionObject"
          detail={
            actionsPending
              ? "WILQ wczytuje kolejkę bezpiecznych akcji. Zapis pozostaje zablokowany."
              : actions.length > 0
              ? actions[0].human_diagnosis || actions[0].recommended_reason
              : "Brak akcji dla tej powierzchni"
          }
          statusLabel={actionsPending ? "wczytywanie" : data.action_summary_label}
          href={actions[0] ? `/actions/${actions[0].id}` : "/actions"}
        />
      </div>
    </section>
  );
}

function ModeRow({
  icon,
  title,
  detail,
  statusLabel,
  href
}: {
  icon: ReactNode;
  title: string;
  detail: string;
  statusLabel: string;
  href: string;
}) {
  return (
    <a href={href} className="grid gap-2 px-4 py-3 hover:bg-slate-50 sm:grid-cols-[1fr_auto]">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-blue-50 text-action">
          {icon}
        </span>
        <span>
          <span className="block text-sm font-semibold text-ink">{title}</span>
          <span className="mt-0.5 line-clamp-2 block text-sm leading-5 text-slate-600">{detail}</span>
        </span>
      </div>
      <StatusPill label={statusLabel} tone="blue" />
    </a>
  );
}

function CompactDiagnosticCard({
  icon,
  title,
  statusLabel,
  summary,
  facts,
  nextStep,
  tone
}: {
  icon: ReactNode;
  title: string;
  statusLabel: string;
  summary: string;
  facts: string[];
  nextStep: string;
  tone: "blue" | "red" | "purple";
}) {
  const toneClasses = {
    blue: "bg-blue-50 text-action",
    red: "bg-red-50 text-risk",
    purple: "bg-violet-50 text-violet-700"
  };

  return (
    <article className="overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="flex items-start justify-between gap-3 border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`flex size-8 items-center justify-center rounded-md ${toneClasses[tone]}`}>
            {icon}
          </span>
          <h2 className="text-base font-semibold text-ink">{title}</h2>
        </div>
        <StatusPill label={statusLabel} tone={tone === "red" ? "red" : tone} />
      </div>
      <div className="p-4">
        <p className="line-clamp-4 text-sm leading-6 text-slate-700">{summary}</p>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          {facts.map((fact) => (
            <div key={fact} className="rounded-md border border-line bg-slate-50 px-3 py-2 text-sm font-medium text-ink">
              {fact}
            </div>
          ))}
        </div>
        <div className="mt-4 border-t border-line pt-3 text-sm leading-6 text-slate-700">
          <span className="font-semibold text-ink">Następny krok: </span>
          {nextStep}
        </div>
      </div>
    </article>
  );
}

function pickPrimaryDecision(data: AdsDiagnosticsResponse) {
  const topIds = data.operator_summary.top_decision_ids;
  return (
    topIds.map((id) => data.decision_queue.find((decision) => decision.id === id)).find(Boolean) ??
    data.decision_queue[0]
  );
}

function priorityFromDecision(decision: AdsDecision): "P1" | "P2" | "P3" | "-" {
  if (decision.status === "blocked" || decision.priority <= 20) return "P1";
  if (decision.priority <= 40) return "P2";
  if (decision.priority <= 70) return "P3";
  return "-";
}

function riskFromDecision(risk: AdsDecision["risk"]): "low" | "medium" | "high" | "blocked" {
  if (risk === "critical") return "high";
  return risk;
}

function uniqueLabels(values: string[]) {
  return Array.from(new Set(values.filter((value) => value.trim().length > 0)));
}

function metricTileValue(data: DemandGenReadinessContract | null, key: string) {
  const value = data?.metric_tiles[key];
  if (value === undefined) return `${key}: brak`;
  return `${key}: ${value}`;
}

function formatCost(totalCostMicros: number, currencyCode?: string | null) {
  const value = totalCostMicros / 1_000_000;
  const formatted = new Intl.NumberFormat("pl-PL", {
    maximumFractionDigits: 2,
    style: currencyCode ? "currency" : "decimal",
    currency: currencyCode ?? undefined
  }).format(value);
  return `koszt ${formatted}`;
}

function dateLabel(value?: string | null) {
  if (!value) return "Dzisiaj";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Dzisiaj";
  return new Intl.DateTimeFormat("pl-PL", {
    day: "numeric",
    month: "long",
    year: "numeric"
  }).format(date);
}
