import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Grid2X2,
  ListChecks,
  MapPin,
  Pencil,
  ShoppingBag,
  Target
} from "lucide-react";

import {
  type ActionObject,
  type CommandCenterResponse,
  type Opportunity,
  type WorkOrder,
  type WorkflowRun,
  getActions,
  getActionsMutationReadiness,
  getCommandCenter,
  getOpportunities,
  getWorkflowRuns,
  getWorkflows
} from "../lib/api";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import {
  CompactStatTile,
  DashboardToolbar,
  DenseQueueTable,
  PriorityBadge,
  RiskPill,
  StatusPill
} from "../components/DashboardMockupPrimitives";
import { ActionList } from "./RegistryPanels";
import { WorkflowRegistryList, WorkflowRunList } from "./WorkflowPanels";

const PRIORITY_ACTION_IDS = [
  "act_review_merchant_feed_issues",
  "act_prepare_content_refresh_queue",
  "act_review_ga4_tracking_quality",
  "act_prepare_ads_campaign_review_queue",
  "act_prepare_negative_keyword_review_queue"
];


type QueueFilter = "all" | "p1" | "blocked" | "ready" | "content" | "ads" | "product" | "local";

type QueueRow = {
  id: string;
  priority: "P1" | "P2" | "P3" | "-";
  type: "decision" | "opportunity" | "action";
  area: "Treści" | "Reklamy" | "Produkty" | "Lokalnie" | "Akcje" | "WILQ";
  title: string;
  detail: string;
  evidence: string;
  risk: "low" | "medium" | "high" | "blocked" | "unknown";
  riskLabel: string;
  status: "ready" | "review" | "blocked" | "done";
  statusLabel: string;
  nextStep: string;
  route: string;
  source: "work_order" | "opportunity" | "action";
};

export function OpportunitiesSurface() {
  const commandCenter = useQuery({ queryKey: ["command-center"], queryFn: getCommandCenter });
  const opportunities = useQuery({ queryKey: ["opportunities"], queryFn: getOpportunities });
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const [filter, setFilter] = useState<QueueFilter>("all");

  if (commandCenter.error && opportunities.error) return <ErrorState />;

  const commandData = commandCenter.data;
  const opportunityItems = opportunities.data ?? [];
  const actionItems = actions.data ?? [];
  const rows = buildQueueRows(commandData, opportunityItems, actionItems);
  const filteredRows = filterQueueRows(rows, filter);
  const selectedRow = filteredRows[0] ?? rows[0];
  const completedRows = buildCompletedRows(commandData, actionItems).slice(0, 3);
  const blockedCount = rows.filter((row) => row.status === "blocked").length;
  const readyCount = rows.filter((row) => row.status === "ready").length;
  const reviewCount = rows.filter((row) => row.status === "review").length;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <DashboardToolbar
        title="Kolejka"
        description="Jedna wspólna kolejka decyzji, blokad i bezpiecznych następnych kroków. Tu nie ma drugiego raportu: to lista pracy do przejścia."
        dateLabel={dateLabel(commandData?.generated_at)}
      />

      <section className="mb-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <CompactStatTile
          value={rows.length}
          label="wszystkie pozycje"
          actionLabel="Zobacz wszystkie"
          tone="blue"
          icon={<ListChecks aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={readyCount}
          label="gotowe do sprawdzenia"
          actionLabel="Zobacz gotowe"
          tone="green"
          icon={<CheckCircle2 aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={reviewCount}
          label="wymaga review"
          actionLabel="Zobacz do review"
          tone="amber"
          icon={<ClipboardList aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={blockedCount}
          label="zablokowane"
          actionLabel="Zobacz blokady"
          tone="red"
          icon={<AlertTriangle aria-hidden="true" size={22} />}
        />
      </section>

      <QueueFilters active={filter} onChange={setFilter} />

      <DenseQueueTable
        title="Kolejka decyzji i akcji"
        rows={filteredRows}
        selectedRowKey={selectedRow?.id}
        getRowKey={(row) => row.id}
        action={
          <select
            className="h-9 rounded-md border border-line bg-white px-3 text-sm font-medium text-slate-700"
            aria-label="Widok kolejki"
            defaultValue="default"
          >
            <option value="default">Domyślny widok</option>
            <option value="risk">Ryzyko najpierw</option>
            <option value="source">Według źródła</option>
          </select>
        }
        columns={[
          {
            key: "priority",
            header: "Priorytet",
            render: (row) => <PriorityBadge value={row.priority} />,
            className: "w-28"
          },
          {
            key: "type",
            header: "Typ",
            render: (row) => queueTypeIcon(row.type),
            className: "w-20"
          },
          {
            key: "area",
            header: "Obszar",
            render: (row) => <span className="font-medium text-slate-700">{row.area}</span>,
            className: "w-32"
          },
          {
            key: "title",
            header: "Tytuł",
            render: (row) => (
              <div className="min-w-72">
                <div className="font-semibold text-ink">{row.title}</div>
                <div className="mt-1 text-xs leading-5 text-slate-500">{row.detail}</div>
              </div>
            )
          },
          {
            key: "evidence",
            header: "Dowody",
            render: (row) => <span className="text-sm leading-5 text-slate-600">{row.evidence}</span>
          },
          {
            key: "risk",
            header: "Ryzyko",
            render: (row) => <RiskPill label={row.riskLabel} risk={row.risk} />,
            className: "w-32"
          },
          {
            key: "status",
            header: "Status",
            render: (row) => <StatusPill label={row.statusLabel} tone={queueStatusTone(row.status)} />,
            className: "w-40"
          },
          {
            key: "next",
            header: "Następny krok",
            render: (row) => (
              <Link to={row.route} className="inline-flex items-center gap-2 text-sm font-medium text-action">
                {row.nextStep}
                <span aria-hidden="true">›</span>
              </Link>
            ),
            className: "min-w-44"
          }
        ]}
      />

      <section className="mt-5 overflow-hidden rounded-md border border-line bg-white shadow-sm">
        <div className="flex min-h-12 items-center justify-between gap-3 border-b border-line px-4 py-3">
          <h2 className="text-base font-semibold text-ink">Ostatnio zakończone</h2>
          <button className="h-9 rounded-md border border-line bg-white px-3 text-sm font-medium text-slate-700" type="button">
            Zobacz wszystkie zakończone
          </button>
        </div>
        <div className="grid gap-0 divide-y divide-line md:grid-cols-3 md:divide-x md:divide-y-0">
          {completedRows.length > 0 ? (
            completedRows.map((row) => (
              <article key={row.id} className="flex items-start gap-3 px-4 py-4">
                <CheckCircle2 aria-hidden="true" size={24} className="mt-1 shrink-0 text-signal" />
                <div>
                  <h3 className="text-sm font-semibold text-ink">{row.title}</h3>
                  <p className="mt-1 text-xs leading-5 text-slate-500">{row.detail}</p>
                  <Link to={row.route} className="mt-2 inline-flex text-sm font-medium text-action">
                    Zobacz dowody
                  </Link>
                </div>
              </article>
            ))
          ) : (
            <div className="px-4 py-5 text-sm text-slate-600 md:col-span-3">
              Brak zakończonych pozycji do pokazania w tym widoku.
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

function QueueFilters({ active, onChange }: { active: QueueFilter; onChange: (value: QueueFilter) => void }) {
  const filters: Array<{ value: QueueFilter; label: string; icon: ReactNode }> = [
    { value: "all", label: "Wszystkie", icon: <Grid2X2 aria-hidden="true" size={16} /> },
    { value: "p1", label: "Priorytet P1", icon: <PriorityBadge value="P1" /> },
    { value: "blocked", label: "Tylko blokady", icon: <AlertTriangle aria-hidden="true" size={16} /> },
    { value: "ready", label: "Tylko gotowe", icon: <CheckCircle2 aria-hidden="true" size={16} /> },
    { value: "content", label: "Treści", icon: <Pencil aria-hidden="true" size={16} /> },
    { value: "ads", label: "Reklamy", icon: <Target aria-hidden="true" size={16} /> },
    { value: "product", label: "Produkty", icon: <ShoppingBag aria-hidden="true" size={16} /> },
    { value: "local", label: "Lokalnie", icon: <MapPin aria-hidden="true" size={16} /> }
  ];

  return (
    <section className="mb-5 flex flex-wrap gap-2">
      {filters.map((item) => (
        <button
          key={item.value}
          type="button"
          onClick={() => onChange(item.value)}
          className={[
            "inline-flex h-11 items-center gap-2 rounded-md border px-4 text-sm font-medium shadow-sm",
            active === item.value
              ? "border-action bg-blue-50 text-action ring-1 ring-action"
              : "border-line bg-white text-slate-700 hover:bg-slate-50"
          ].join(" ")}
        >
          {item.icon}
          {item.label}
        </button>
      ))}
    </section>
  );
}

function buildQueueRows(
  commandCenter: CommandCenterResponse | undefined,
  opportunities: Opportunity[],
  actions: ActionObject[]
): QueueRow[] {
  const workOrderRows = (commandCenter?.work_orders ?? []).map(workOrderToQueueRow);
  const existingIds = new Set(workOrderRows.map((row) => row.id));
  const opportunityRows = opportunities
    .filter((item) => !existingIds.has(item.id))
    .map(opportunityToQueueRow);
  const actionRows = actions
    .filter((action) => shouldShowActionInUnifiedQueue(action, commandCenter, opportunities))
    .slice(0, 8)
    .map(actionToQueueRow);

  return [...workOrderRows, ...opportunityRows, ...actionRows]
    .sort((left, right) => queuePriorityRank(left.priority) - queuePriorityRank(right.priority));
}

function workOrderToQueueRow(item: WorkOrder): QueueRow {
  return {
    id: item.id,
    priority: priorityFromNumber(item.priority, item.status === "blocked" ? "P1" : undefined),
    type: "decision",
    area: areaFromDomain(item.domain),
    title: item.title,
    detail: item.why_it_matters || item.summary,
    evidence: item.evidence_summary || evidenceCountLabel(item.evidence_ids.length),
    risk: queueRisk(item.risk),
    riskLabel: riskLabel(item.risk),
    status: item.status === "blocked" ? "blocked" : item.status === "done" ? "done" : "review",
    statusLabel: item.status_label || statusLabelFromQueueStatus(item.status === "blocked" ? "blocked" : "review"),
    nextStep: shortNextStep(item.next_safe_step, item.route_label),
    route: item.route,
    source: "work_order"
  };
}

function opportunityToQueueRow(item: Opportunity): QueueRow {
  const status: QueueRow["status"] = item.risk === "high" ? "blocked" : "review";
  return {
    id: item.id,
    priority: item.risk === "high" ? "P1" : item.risk === "medium" ? "P2" : "P3",
    type: "opportunity",
    area: areaFromDomain(item.domain),
    title: item.title,
    detail: item.human_diagnosis,
    evidence: item.evidence_summary_label || evidenceCountLabel(item.evidence_ids.length),
    risk: queueRisk(item.risk),
    riskLabel: item.risk_label || riskLabel(item.risk),
    status,
    statusLabel: status === "blocked" ? "Zablokowane" : "Wymaga review",
    nextStep: shortNextStep(item.recommended_action, areaRouteLabel(item.domain)),
    route: routeFromDomain(item.domain),
    source: "opportunity"
  };
}

function actionToQueueRow(action: ActionObject): QueueRow {
  const status: QueueRow["status"] = action.validation_status === "valid" ? "ready" : "review";
  return {
    id: action.id,
    priority: action.risk === "high" ? "P1" : action.risk === "medium" ? "P2" : "P3",
    type: "action",
    area: areaFromDomain(action.domain),
    title: action.title,
    detail: action.recommended_reason || action.human_diagnosis,
    evidence: evidenceCountLabel(action.evidence_ids.length),
    risk: queueRisk(action.risk),
    riskLabel: riskLabel(action.risk),
    status,
    statusLabel: status === "ready" ? "Gotowe do sprawdzenia" : "Wymaga review",
    nextStep: "Otwórz akcję",
    route: `/actions/${action.id}`,
    source: "action"
  };
}

function shouldShowActionInUnifiedQueue(
  action: ActionObject,
  commandCenter: CommandCenterResponse | undefined,
  opportunities: Opportunity[]
) {
  const referencedActionIds = new Set([
    ...(commandCenter?.work_orders.flatMap((item) => item.action_ids) ?? []),
    ...opportunities.flatMap((item) => item.action_ids)
  ]);
  return !referencedActionIds.has(action.id) || PRIORITY_ACTION_IDS.includes(action.id);
}

function buildCompletedRows(
  commandCenter: CommandCenterResponse | undefined,
  actions: ActionObject[]
): QueueRow[] {
  const doneWorkOrders = (commandCenter?.work_orders ?? [])
    .filter((item) => item.status === "done")
    .map(workOrderToQueueRow);
  const validActions = actions
    .filter((action) => action.validation_status === "valid")
    .slice(0, 3)
    .map(actionToQueueRow)
    .map((row) => ({ ...row, status: "done" as const, statusLabel: "Zakończone" }));
  return [...doneWorkOrders, ...validActions];
}

function filterQueueRows(rows: QueueRow[], filter: QueueFilter) {
  if (filter === "all") return rows;
  if (filter === "p1") return rows.filter((row) => row.priority === "P1");
  if (filter === "blocked") return rows.filter((row) => row.status === "blocked");
  if (filter === "ready") return rows.filter((row) => row.status === "ready");
  if (filter === "content") return rows.filter((row) => row.area === "Treści");
  if (filter === "ads") return rows.filter((row) => row.area === "Reklamy");
  if (filter === "product") return rows.filter((row) => row.area === "Produkty");
  if (filter === "local") return rows.filter((row) => row.area === "Lokalnie");
  return rows;
}

function queueTypeIcon(type: QueueRow["type"]) {
  if (type === "decision") return <ClipboardList aria-label="decyzja" size={18} className="text-slate-600" />;
  if (type === "opportunity") return <Target aria-label="szansa" size={18} className="text-slate-600" />;
  return <CheckCircle2 aria-label="akcja" size={18} className="text-slate-600" />;
}

function queueStatusTone(status: QueueRow["status"]) {
  if (status === "ready" || status === "done") return "green" as const;
  if (status === "blocked") return "red" as const;
  return "amber" as const;
}

function queuePriorityRank(priority: QueueRow["priority"]) {
  if (priority === "P1") return 1;
  if (priority === "P2") return 2;
  if (priority === "P3") return 3;
  return 4;
}

function priorityFromNumber(priority: number, fallback?: QueueRow["priority"]): QueueRow["priority"] {
  if (priority <= 1) return "P1";
  if (priority === 2) return "P2";
  if (priority >= 3) return "P3";
  return fallback ?? "-";
}

function areaFromDomain(domain: string): QueueRow["area"] {
  if (domain.includes("content") || domain.includes("seo") || domain.includes("knowledge")) return "Treści";
  if (domain.includes("ads") || domain.includes("ga4") || domain.includes("demand")) return "Reklamy";
  if (domain.includes("merchant") || domain.includes("product")) return "Produkty";
  if (domain.includes("local") || domain.includes("localo")) return "Lokalnie";
  if (domain.includes("action")) return "Akcje";
  return "WILQ";
}

function routeFromDomain(domain: string) {
  const area = areaFromDomain(domain);
  if (area === "Treści") return "/content-planner";
  if (area === "Reklamy") return "/ads-doctor";
  if (area === "Produkty") return "/merchant";
  if (area === "Lokalnie") return "/localo";
  if (area === "Akcje") return "/actions";
  return "/command-center";
}

function areaRouteLabel(domain: string) {
  const area = areaFromDomain(domain);
  if (area === "Treści") return "Otwórz treści";
  if (area === "Reklamy") return "Otwórz reklamy";
  if (area === "Produkty") return "Otwórz Merchant";
  if (area === "Lokalnie") return "Otwórz Localo";
  if (area === "Akcje") return "Otwórz akcje";
  return "Otwórz WILQ";
}

function queueRisk(risk: string): QueueRow["risk"] {
  if (risk === "critical" || risk === "high") return "high";
  if (risk === "medium") return "medium";
  if (risk === "low") return "low";
  return "unknown";
}

function riskLabel(risk: string) {
  if (risk === "critical" || risk === "high") return "wysokie";
  if (risk === "medium") return "średnie";
  if (risk === "low") return "niskie";
  return "do oceny";
}

function statusLabelFromQueueStatus(status: QueueRow["status"]) {
  if (status === "ready") return "Gotowe do sprawdzenia";
  if (status === "blocked") return "Zablokowane";
  if (status === "done") return "Zakończone";
  return "Wymaga review";
}

function evidenceCountLabel(count: number) {
  if (count === 1) return "1 dowód";
  if (count > 1 && count < 5) return `${count} dowody`;
  return `${count} dowodów`;
}

function shortNextStep(text: string, fallback: string) {
  const trimmed = text.trim();
  if (!trimmed) return fallback;
  if (trimmed.length <= 32) return trimmed;
  if (/merchant/i.test(trimmed)) return "Otwórz Merchant";
  if (/ga4|pomiar/i.test(trimmed)) return "Otwórz GA4";
  if (/ads|kampani|google/i.test(trimmed)) return "Otwórz Google Ads";
  if (/treś|content|seo|brief/i.test(trimmed)) return "Otwórz treści";
  if (/localo|lokal/i.test(trimmed)) return "Otwórz Localo";
  return fallback;
}

function dateLabel(value: string | null | undefined) {
  if (!value) return "Dzisiaj";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Dzisiaj";
  return new Intl.DateTimeFormat("pl-PL", {
    day: "numeric",
    month: "long",
    year: "numeric"
  }).format(date);
}

export function ActionsSurface() {
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const mutationReadiness = useQuery({
    queryKey: ["actions", "mutation-readiness"],
    queryFn: getActionsMutationReadiness
  });
  const [showFullList, setShowFullList] = useState(false);

  if (actions.isLoading) return <LoadingBand />;
  if (actions.error) return <ErrorState />;

  const items = actions.data ?? [];
  const evidenceIds = new Set(items.flatMap((action) => action.evidence_ids));
  const needsValidation = items.filter(
    (action) => action.validation_status !== "valid"
  );
  const priorityActions = getPriorityActions(items);
  const remainingActions = items.filter(
    (action) => !priorityActions.some((focusAction) => focusAction.id === action.id)
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <SurfaceIntro
        title="Akcje do sprawdzenia"
        description="Kolejka sprawdzeń przygotowana przez WILQ. Na wejściu pokazuje tylko najważniejsze decyzje, dowody, ryzyko i następny krok. Zapis zmian pozostaje zablokowany bez sprawdzenia w WILQ, jawnej zgody i audytu."
        metrics={[
          { label: "Akcje", value: items.length },
          { label: "Do sprawdzenia", value: needsValidation.length },
          { label: "Dowody", value: evidenceIds.size }
        ]}
      />

      <div className="grid gap-8">
        <FirstWriteCandidateSection
          isLoading={mutationReadiness.isLoading}
          error={mutationReadiness.error}
          summary={mutationReadiness.data}
        />
        <section>
          <SectionHeading title="Najważniejsze na start" />
          <p className="mb-3 max-w-3xl text-sm leading-6 text-slate-600">
            Zacznij od sprawdzeń, które odpowiadają głównej ścieżce pracy:
            Merchant, treści, GA4 i Google Ads. Pełna lista zostaje schowana,
            dopóki nie jest potrzebna.
          </p>
          <ActionPriorityFocus actions={priorityActions} />
        </section>
        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionHeading title="Pozostałe akcje" />
            <ToggleButton onClick={() => setShowFullList((value) => !value)}>
              {showFullList ? "Ukryj pozostałe akcje" : `Pokaż pozostałe akcje (${remainingActions.length})`}
            </ToggleButton>
          </div>
          {showFullList ? (
            <ActionList actions={remainingActions} />
          ) : (
            <MutedExpandableText>
              Pozostałe akcje są dostępne po rozwinięciu. Domyślny widok ma pomagać wybrać
              następne sprawdzenie, nie przeglądać całej kolejki naraz.
            </MutedExpandableText>
          )}
        </section>
      </div>
    </main>
  );
}

function FirstWriteCandidateSection({
  isLoading,
  error,
  summary
}: {
  isLoading: boolean;
  error: unknown;
  summary: Awaited<ReturnType<typeof getActionsMutationReadiness>> | undefined;
}) {
  if (isLoading) {
    return (
      <section>
        <SectionHeading title="Pierwsza propozycja zapisu" />
        <LoadingBand />
      </section>
    );
  }
  if (error || !summary?.first_write_candidate) {
    return (
      <section>
        <SectionHeading title="Pierwsza propozycja zapisu" />
        <BlockerNotice message="WILQ nie wskazał jeszcze pierwszej bezpiecznej klasy zapisu. Nie uruchamiaj write adapterów bez osobnego readiness." />
      </section>
    );
  }

  const candidate = summary.first_write_candidate;
  const blockerLabels = candidate.blockers.slice(0, 5).map((blocker) => blocker.label);

  return (
    <section className="rounded-md border border-action/30 bg-action/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <SectionHeading title="Pierwsza propozycja zapisu" />
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">
            {summary.first_write_candidate_reason}
          </p>
        </div>
        <StatusBadge
          value={candidate.vendor_write_possible ? "ready" : "blocked"}
          label={candidate.vendor_write_possible ? "write możliwy" : "write zablokowany"}
        />
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <h3 className="text-sm font-semibold">{candidate.title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {candidate.operator_next_step}
          </p>
          {candidate.target_label ? (
            <p className="mt-2 rounded-md border border-line bg-white p-2 text-xs leading-5 text-slate-600">
              Propozycja treści: {candidate.target_label}
            </p>
          ) : null}
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusBadge value={candidate.mode} label={candidate.mode_label} />
            <StatusBadge value={candidate.risk} label={candidate.risk_label} />
            <StatusBadge value={candidate.validation_status} label={candidate.validation_status} />
          </div>
          <Link
            to="/actions/$actionId"
            params={{ actionId: candidate.action_id }}
            className="mt-4 inline-flex min-h-9 items-center rounded-md border border-action bg-white px-3 py-2 text-xs font-medium text-action hover:bg-action/10"
          >
            Otwórz propozycję
          </Link>
        </div>
        <div className="rounded-md border border-slate-200 bg-white p-3 text-sm leading-6 text-slate-700">
          <div className="font-semibold text-slate-900">Co nadal blokuje zapis</div>
          {blockerLabels.length > 0 ? (
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {blockerLabels.map((label) => (
                <li key={label}>{label}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2">WILQ nie zgłosił blokad, ale nadal wymagaj preview, review i confirm.</p>
          )}
          <p className="mt-3 text-xs leading-5 text-slate-500">
            Stan całego systemu: {summary.vendor_write_possible_count} gotowych write adapterów,
            {summary.would_attempt_vendor_write_count} akcji próbowałoby zapisu.
          </p>
        </div>
      </div>
      <div className="mt-4 rounded-md border border-line bg-white p-3 text-sm leading-6 text-slate-700">
        <div className="font-semibold text-slate-900">Plan aktywacji bez ryzyka</div>
        <p className="mt-2">{summary.activation_next_step}</p>
        <ol className="mt-2 list-decimal space-y-1 pl-5">
          {summary.activation_plan_steps.slice(0, 5).map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </div>
      {candidate.apply_contract ? (
        <div className="mt-4 rounded-md border border-line bg-white p-3 text-sm leading-6 text-slate-700">
          <div className="font-semibold text-slate-900">Kontrakt przyszłego apply</div>
          <p className="mt-2">{candidate.apply_contract.operator_summary}</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            <ReadinessTile
              label="Operacja"
              value={candidate.apply_contract.allowed_operation}
            />
            <ReadinessTile
              label="Adapter"
              value={candidate.apply_contract.adapter_status === "implemented" ? "gotowy" : "brak"}
            />
            <ReadinessTile
              label="Publikacja"
              value={candidate.apply_contract.publication_allowed ? "dozwolona" : "zablokowana"}
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}

function getPriorityActions(actions: ActionObject[]) {
  const byId = new Map(actions.map((action) => [action.id, action]));
  return PRIORITY_ACTION_IDS.map((id) => byId.get(id)).filter(
    (action): action is ActionObject => Boolean(action)
  );
}

function ReadinessTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3 text-sm">
      <div className="text-xs font-medium uppercase tracking-normal text-slate-500">{label}</div>
      <div className="mt-1 font-semibold text-ink">{value}</div>
    </div>
  );
}

function ActionPriorityFocus({ actions }: { actions: ActionObject[] }) {
  if (actions.length === 0) {
    return (
      <BlockerNotice message="Brak priorytetowych akcji z głównej ścieżki pracy. Pełna lista niżej nadal pokazuje dostępne akcje do sprawdzenia." />
    );
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {actions.map((action) => (
        <article key={action.id} className="rounded-md border border-action/30 bg-action/5 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{action.title}</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                Zanim cokolwiek zapiszesz, otwórz akcję i sprawdź dowody, podgląd zmian
                oraz decyzję człowieka.
              </p>
            </div>
            <StatusBadge value={action.validation_status} label={action.validation_status_label} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            {action.recommended_reason}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusBadge value={action.status} label={action.status_label} />
            <StatusBadge value={action.risk} label={action.risk_label} />
          </div>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Dowody: {action.evidence_summary_label}</div>
            <div>Metryki: {action.metrics.length}</div>
          </div>
          <Link
            to="/actions/$actionId"
            params={{ actionId: action.id }}
            className="mt-4 inline-flex min-h-9 items-center rounded-md border border-action bg-white px-3 py-2 text-xs font-medium text-action hover:bg-action/10"
          >
            Otwórz akcję
          </Link>
        </article>
      ))}
    </div>
  );
}

export function WorkflowsSurface() {
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: getWorkflows });
  const workflowRuns = useQuery({ queryKey: ["workflow-runs"], queryFn: getWorkflowRuns });
  const [showRelatedActions, setShowRelatedActions] = useState(false);
  const [showWorkflowRuns, setShowWorkflowRuns] = useState(false);
  const [showWorkflowOutcomes, setShowWorkflowOutcomes] = useState(false);
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions,
    enabled: showRelatedActions
  });

  if (workflows.isLoading) {
    return <LoadingBand />;
  }
  if (workflows.error) {
    return <ErrorState />;
  }

  const runs = workflowRuns.data ?? [];
  const workflowItems = workflows.data ?? [];
  const readyWorkflows = workflowItems.filter((workflow) => workflow.status === "ready");
  const workflowEvidenceIds = new Set([
    ...runs.flatMap((run) => run.output.evidence_ids),
    ...workflowItems.flatMap((workflow) => workflow.evidence_ids)
  ]);
  const workflowActionIds = new Set([
    ...runs.flatMap((run) => run.output.action_ids),
    ...workflowItems.flatMap((workflow) => workflow.action_ids)
  ]);
  const workflowLabelsById = new Map(workflowItems.map((workflow) => [workflow.id, workflow.label]));
  const relatedActions = (actions.data ?? []).filter((action) => workflowActionIds.has(action.id));

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <SurfaceIntro
        title="Procesy WILQ"
        description="Procesy łączą decyzje, dowody i akcje do sprawdzenia. Gotowe prowadzą do pracy marketera, a zablokowane pokazują, czego WILQ nie może jeszcze bezpiecznie obiecać ani zapisać."
        metrics={[
          { label: "Procesy", value: workflowItems.length },
          { label: "Gotowe", value: readyWorkflows.length },
          { label: "Uruchomienia", value: runs.length }
        ]}
      />

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Procesy decyzyjne" />
          <WorkflowRegistryList workflows={workflowItems} />
        </section>
        <WorkflowRunsSection
          runs={runs}
          workflowLabelsById={workflowLabelsById}
          isLoading={workflowRuns.isLoading}
          error={workflowRuns.error}
          expanded={showWorkflowRuns}
          onToggle={() => setShowWorkflowRuns((value) => !value)}
        />
        <WorkflowOutcomesSection
          evidenceCount={workflowEvidenceIds.size}
          actionCount={workflowActionIds.size}
          expanded={showWorkflowOutcomes}
          onToggle={() => setShowWorkflowOutcomes((value) => !value)}
        />
        <RelatedWorkflowActionsSection
          actionCount={workflowActionIds.size}
          actions={relatedActions}
          isLoading={actions.isLoading}
          error={actions.error}
          expanded={showRelatedActions}
          onToggle={() => setShowRelatedActions((value) => !value)}
        />
      </div>
    </main>
  );
}

type SurfaceMetric = {
  label: string;
  value: string | number;
};

function SurfaceIntro({
  title,
  description,
  metrics
}: {
  title: string;
  description: string;
  metrics: SurfaceMetric[];
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        {metrics.map((metric) => (
          <MetricTile key={metric.label} label={metric.label} value={metric.value} />
        ))}
      </div>
    </div>
  );
}

function ToggleButton({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex min-h-9 items-center rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
    >
      {children}
    </button>
  );
}

function MutedExpandableText({ children }: { children: ReactNode }) {
  return (
    <p className="mt-2 rounded-md border border-line bg-white p-3 text-sm leading-6 text-slate-600">
      {children}
    </p>
  );
}

function WorkflowRunsSection({
  runs,
  workflowLabelsById,
  isLoading,
  error,
  expanded,
  onToggle
}: {
  runs: WorkflowRun[];
  workflowLabelsById: Map<string, string>;
  isLoading: boolean;
  error: unknown;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeading title="Ostatnie uruchomienia" />
        {!isLoading && !error ? (
          <ToggleButton onClick={onToggle}>
            {expanded ? "Ukryj uruchomienia" : `Pokaż uruchomienia (${runs.length})`}
          </ToggleButton>
        ) : null}
      </div>
      {isLoading ? (
        <LoadingBand />
      ) : error ? (
        <InlineErrorState message="Nie udało się pobrać historii uruchomień." />
      ) : expanded ? (
        <WorkflowRunList runs={runs} workflowLabelsById={workflowLabelsById} />
      ) : (
        <MutedExpandableText>
          Historia uruchomień jest schowana na wejściu. Najpierw wybierz proces albo
          przejdź do widoku pracy, a uruchomienia sprawdzaj tylko przy audycie.
        </MutedExpandableText>
      )}
    </section>
  );
}

function WorkflowOutcomesSection({
  evidenceCount,
  actionCount,
  expanded,
  onToggle
}: {
  evidenceCount: number;
  actionCount: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeading title="Wyniki procesów" />
        <ToggleButton onClick={onToggle}>
          {expanded ? "Ukryj wyniki" : "Pokaż wyniki procesów"}
        </ToggleButton>
      </div>
      {expanded ? (
        <div className="grid gap-3 xl:grid-cols-2">
          <WorkflowOutcomeCard
            title="Dowody z procesów"
            count={evidenceCount}
            suffix="powiązanych dowodów"
            detail="Szczegółowe ID zostają w widokach technicznych."
          />
          <WorkflowOutcomeCard
            title="Akcje z procesów"
            count={actionCount}
            suffix="powiązanych akcji do sprawdzenia"
            detail="Pełne szczegóły są niżej w kartach akcji."
          />
        </div>
      ) : (
        <MutedExpandableText>
          Wyniki procesów są dostępne po rozwinięciu. Domyślny widok pokazuje
          priorytet, status i bezpieczny następny krok.
        </MutedExpandableText>
      )}
    </section>
  );
}

function WorkflowOutcomeCard({
  title,
  count,
  suffix,
  detail
}: {
  title: string;
  count: number;
  suffix: string;
  detail: string;
}) {
  const outcomeCopy =
    count > 0
      ? `WILQ ma ${count} ${suffix}. ${detail}`
      : `WILQ nie ma jeszcze ${suffix}. Nie traktuj tego procesu jak gotowej decyzji bez dowodów i akcji do sprawdzenia. ${detail}`;

  return (
    <article className="rounded-md border border-line bg-white p-4 text-sm text-slate-700">
      <h3 className="font-semibold text-ink">{title}</h3>
      <p className="mt-2 leading-6">{outcomeCopy}</p>
    </article>
  );
}

function RelatedWorkflowActionsSection({
  actionCount,
  actions,
  isLoading,
  error,
  expanded,
  onToggle
}: {
  actionCount: number;
  actions: ActionObject[];
  isLoading: boolean;
  error: unknown;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeading title="Powiązane akcje" />
        <ToggleButton onClick={onToggle}>
          {expanded ? "Ukryj powiązane akcje" : `Pokaż powiązane akcje (${actionCount})`}
        </ToggleButton>
      </div>
      {isLoading ? (
        <LoadingBand />
      ) : error ? (
        <InlineErrorState message="Nie udało się pobrać powiązanych akcji." />
      ) : expanded ? (
        <ActionList actions={actions} />
      ) : (
        <MutedExpandableText>
          Pełne karty akcji są dostępne po rozwinięciu. Wejście w procesy ma
          najpierw pokazać, co jest gotowe, co jest zablokowane i gdzie przejść dalej.
        </MutedExpandableText>
      )}
    </section>
  );
}

function SectionHeading({ title }: { title: string }) {
  return <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-slate-600">{title}</h2>;
}

function ErrorState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="rounded-md border border-risk/30 bg-risk/10 p-4 text-sm text-risk">
        Nie udało się połączyć z WILQ.
      </div>
    </main>
  );
}

function InlineErrorState({ message }: { message: string }) {
  return <BlockerNotice message={message} />;
}
