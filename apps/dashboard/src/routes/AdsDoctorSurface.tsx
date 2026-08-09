import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  CheckCircle2,
  Gauge,
  LineChart,
  Megaphone,
  RefreshCw,
  ShieldAlert,
  Sparkles
} from "lucide-react";

import {
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
import { AdsDiagnosticsLoadingState } from "./AdsDoctorSections/AdsDiagnosticsLoadingState";
import { CompactDiagnosticCard } from "./AdsDoctorSections/CompactDiagnosticCard";
import { MeasurementFirstBanner } from "./AdsDoctorSections/MeasurementFirstBanner";
import { SafeWorkModes } from "./AdsDoctorSections/SafeWorkModes";
import {
  dateLabel,
  formatCost,
  metricTileValue,
  pickPrimaryDecision,
  priorityFromDecision,
  riskFromDecision,
  uniqueLabels
} from "./AdsDoctorSections/formatters";

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
