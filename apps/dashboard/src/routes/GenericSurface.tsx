import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, FileJson, RefreshCw, ShieldCheck } from "lucide-react";
import { useState } from "react";

import {
  getConnectors,
  getConnectorRefreshRun,
  getKnowledgeCards,
  getKnowledgeOperatingMap,
  getKnowledgePlaybooks,
  refreshConnector,
  getWorkflowRuns,
  getWorkflows,
  type ConnectorRefreshRun,
  type ConnectorStatus,
  type KnowledgeCard,
  type KnowledgeOperatingMapResponse,
  type MarketingPlaybook,
  type Workflow,
  type WorkflowRun
} from "../lib/api";
import { BlockerNotice, LoadingBand } from "../components/OperatorPrimitives";
import {
  CompactRoutePanel,
  compactRouteConfig,
  type CompactRouteConfig
} from "./CompactRoutePanel";
import {
  KnowledgeCardList,
  KnowledgeOperatingMapPanel,
  PlaybookList
} from "./KnowledgePanels";
import { ConnectorGrid } from "./RegistryPanels";
import { WorkflowRunList } from "./WorkflowPanels";

export function GenericSurface({ routeName }: { routeName: string }) {
  const compactRoute = compactRouteConfig(routeName);
  const routeKind = genericRouteKind(routeName, compactRoute);
  const [showKnowledgeMap, setShowKnowledgeMap] = useState(false);
  const [showKnowledgeCards, setShowKnowledgeCards] = useState(false);
  const [showKnowledgePlaybooks, setShowKnowledgePlaybooks] = useState(false);
  const connectors = useQuery({
    queryKey: ["connectors"],
    queryFn: getConnectors,
    enabled: routeKind === "settings" || routeKind === "system"
  });
  const workflows = useQuery({
    queryKey: ["workflows"],
    queryFn: getWorkflows,
    enabled: routeKind === "workflow" || routeKind === "system"
  });
  const workflowRuns = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: getWorkflowRuns,
    enabled: routeKind === "workflow" || routeKind === "system"
  });
  const knowledgeMap = useQuery({
    queryKey: ["knowledge-operating-map"],
    queryFn: getKnowledgeOperatingMap,
    enabled: routeKind === "knowledge"
  });
  const knowledgeCards = useQuery({
    queryKey: ["knowledge-cards"],
    queryFn: getKnowledgeCards,
    enabled: routeKind === "knowledge" && showKnowledgeCards
  });
  const playbooks = useQuery({
    queryKey: ["knowledge-playbooks"],
    queryFn: getKnowledgePlaybooks,
    enabled: routeKind === "knowledge" && showKnowledgePlaybooks
  });
  if (isGenericSurfaceLoading(routeKind, connectors, workflows, workflowRuns)) {
    return <LoadingBand />;
  }
  if (hasGenericSurfaceError(routeKind, connectors, workflows, workflowRuns)) {
    return <ErrorState />;
  }

  const header = genericSurfaceHeader(routeKind, compactRoute);
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <SurfaceHeader title={header.title} description={header.description} />
      <GenericSurfaceSections
        routeKind={routeKind}
        compactRoute={compactRoute}
        connectors={connectors.data ?? []}
        workflows={workflows.data ?? []}
        workflowRuns={workflowRuns.data ?? []}
        knowledgeMap={knowledgeMap}
        knowledgeCards={knowledgeCards}
        playbooks={playbooks}
        showKnowledgeMap={showKnowledgeMap}
        setShowKnowledgeMap={setShowKnowledgeMap}
        showKnowledgeCards={showKnowledgeCards}
        setShowKnowledgeCards={setShowKnowledgeCards}
        showKnowledgePlaybooks={showKnowledgePlaybooks}
        setShowKnowledgePlaybooks={setShowKnowledgePlaybooks}
      />
    </main>
  );
}

type GenericRouteKind = "knowledge" | "workflow" | "settings" | "system" | "compact" | "generic";

function genericRouteKind(
  routeName: string,
  compactRoute: CompactRouteConfig | undefined
): GenericRouteKind {
  if (routeName.startsWith("/knowledge")) return "knowledge";
  if (routeName.startsWith("/workflows")) return "workflow";
  if (routeName.startsWith("/settings")) return "settings";
  if (routeName.startsWith("/system")) return "system";
  if (compactRoute) return "compact";
  return "generic";
}

function isGenericSurfaceLoading(
  routeKind: GenericRouteKind,
  connectors: UseQueryResult<ConnectorStatus[]>,
  workflows: UseQueryResult<Workflow[]>,
  workflowRuns: UseQueryResult<WorkflowRun[]>
) {
  if (routeKind === "settings") return connectors.isLoading;
  if (routeKind === "system") return connectors.isLoading || workflows.isLoading || workflowRuns.isLoading;
  if (routeKind === "workflow") return workflows.isLoading || workflowRuns.isLoading;
  return false;
}

function hasGenericSurfaceError(
  routeKind: GenericRouteKind,
  connectors: UseQueryResult<ConnectorStatus[]>,
  workflows: UseQueryResult<Workflow[]>,
  workflowRuns: UseQueryResult<WorkflowRun[]>
) {
  if (routeKind === "settings") return Boolean(connectors.error);
  if (routeKind === "system") return Boolean(connectors.error || workflows.error || workflowRuns.error);
  if (routeKind === "workflow") return Boolean(workflows.error || workflowRuns.error);
  return false;
}

function genericSurfaceHeader(
  routeKind: GenericRouteKind,
  compactRoute: CompactRouteConfig | undefined
) {
  if (routeKind === "knowledge") {
    return {
      title: "Wiedza",
      description:
        "Wiedza oparta na źródłach, twierdzenia usług, status review i stan zatwierdzenia."
    };
  }
  if (routeKind === "settings") {
    return {
      title: "Źródła",
      description:
        "Zdrowie źródeł, aktualność danych i dostęp wpływają na jakość decyzji."
    };
  }
  if (routeKind === "system") {
    return {
      title: "System",
      description:
        "Przegląd audytowy: status procesów, uruchomienia Codex, historia operatora i reguły bezpieczeństwa."
    };
  }
  return {
    title: compactRoute?.title ?? "Widok WILQ",
    description: "Powierzchnia WILQ z dowodami, źródłami danych i stanem akcji."
  };
}

function GenericSurfaceSections({
  routeKind,
  compactRoute,
  connectors,
  workflows,
  workflowRuns,
  knowledgeMap,
  knowledgeCards,
  playbooks,
  showKnowledgeMap,
  setShowKnowledgeMap,
  showKnowledgeCards,
  setShowKnowledgeCards,
  showKnowledgePlaybooks,
  setShowKnowledgePlaybooks
}: {
  routeKind: GenericRouteKind;
  compactRoute: CompactRouteConfig | undefined;
  connectors: ConnectorStatus[];
  workflows: Workflow[];
  workflowRuns: WorkflowRun[];
  knowledgeMap: UseQueryResult<KnowledgeOperatingMapResponse>;
  knowledgeCards: UseQueryResult<KnowledgeCard[]>;
  playbooks: UseQueryResult<MarketingPlaybook[]>;
  showKnowledgeMap: boolean;
  setShowKnowledgeMap: (value: boolean | ((current: boolean) => boolean)) => void;
  showKnowledgeCards: boolean;
  setShowKnowledgeCards: (value: boolean | ((current: boolean) => boolean)) => void;
  showKnowledgePlaybooks: boolean;
  setShowKnowledgePlaybooks: (value: boolean | ((current: boolean) => boolean)) => void;
}) {
  return (
    <div className="grid gap-6">
      {routeKind === "workflow" ? (
        <WorkflowSurfaceSections workflows={workflows} workflowRuns={workflowRuns} />
      ) : null}
      {routeKind === "knowledge" ? (
        <KnowledgeSurfaceSections
          knowledgeMap={knowledgeMap}
          knowledgeCards={knowledgeCards}
          playbooks={playbooks}
          showKnowledgeMap={showKnowledgeMap}
          setShowKnowledgeMap={setShowKnowledgeMap}
          showKnowledgeCards={showKnowledgeCards}
          setShowKnowledgeCards={setShowKnowledgeCards}
          showKnowledgePlaybooks={showKnowledgePlaybooks}
          setShowKnowledgePlaybooks={setShowKnowledgePlaybooks}
        />
      ) : null}
      {routeKind === "settings" ? <SettingsSurfaceSections connectors={connectors} /> : null}
      {routeKind === "system" ? (
        <SystemSurfaceSections
          connectors={connectors}
          workflows={workflows}
          workflowRuns={workflowRuns}
        />
      ) : null}
      {compactRoute ? <CompactRoutePanel config={compactRoute} /> : null}
    </div>
  );
}

function SurfaceHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="mb-6 flex items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
        <p className="mt-1 text-sm text-slate-600">{description}</p>
      </div>
      <FileJson aria-hidden="true" className="text-action" size={28} />
    </div>
  );
}

function WorkflowSurfaceSections({
  workflows,
  workflowRuns
}: {
  workflows: Workflow[];
  workflowRuns: WorkflowRun[];
}) {
  return (
    <>
      <section>
        <SectionHeading title="Procesy decyzyjne" />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {workflows.map((workflow) => (
            <article key={workflow.id} className="rounded-md border border-line bg-white p-4">
              <h3 className="text-sm font-semibold">{workflow.label}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-700">{workflow.description}</p>
            </article>
          ))}
        </div>
      </section>
      <section>
        <SectionHeading title="Ostatnie uruchomienia" />
        <WorkflowRunList runs={workflowRuns} />
      </section>
    </>
  );
}

function SystemSurfaceSections({
  connectors,
  workflows,
  workflowRuns
}: {
  connectors: ConnectorStatus[];
  workflows: Workflow[];
  workflowRuns: WorkflowRun[];
}) {
  const technicalReviewCount = workflows.filter((workflow) =>
    workflow.status !== "ready" || workflow.risk !== "low"
  ).length;
  const blockedSecurityRules = systemSecurityRows().filter((row) => row.status === "blocked").length;
  const activeConnectors = connectors.filter((connector) => connector.configured).length;
  const workflowLabels = new Map(workflows.map((workflow) => [workflow.id, workflow.label]));

  return (
    <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SourceStatTile value={workflows.length} label="procesów" tone="default" />
        <SourceStatTile value={workflowRuns.length} label="ostatnie uruchomienia" tone="default" />
        <SourceStatTile value={technicalReviewCount} label="obszary techniczne w review" tone="wait" />
        <SourceStatTile value={blockedSecurityRules} label="blokady systemowe" tone="risk" />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <article className="rounded-md border border-line bg-white">
          <SystemPanelHeader title="Procesy" cta="Zobacz wszystkie" href="/workflows" />
          <div className="divide-y divide-line">
            {workflows.slice(0, 3).map((workflow) => (
              <SystemListRow
                key={workflow.id}
                title={workflow.label}
                description={workflow.description}
                status={workflow.status === "ready" ? "gotowe" : workflow.status_label ?? workflow.status}
                statusClass={workflow.status === "ready" ? "bg-success/10 text-success" : "bg-wait/10 text-wait"}
              />
            ))}
          </div>
          <div className="border-t border-line px-4 py-3 text-sm text-slate-600">
            Łącznie {workflows.length} procesów
          </div>
        </article>

        <article className="rounded-md border border-line bg-white">
          <SystemPanelHeader title="Uruchomienia Codex" cta="Zobacz wszystkie" href="/codex-runs" />
          <div className="divide-y divide-line">
            {workflowRuns.slice(0, 3).map((run) => (
              <SystemListRow
                key={run.id}
                title={workflowLabels.get(run.workflow_id) ?? "Proces WILQ"}
                description={formatSystemRunDescription(run)}
                status={run.status_label}
                statusClass={run.status === "failed" ? "bg-risk/10 text-risk" : "bg-success/10 text-success"}
              />
            ))}
            {workflowRuns.length === 0 ? (
              <div className="px-4 py-3 text-sm text-slate-600">
                Brak zapisanych uruchomień do pokazania.
              </div>
            ) : null}
          </div>
          <div className="border-t border-line px-4 py-3">
            <a href="/codex-runs" className="text-sm font-semibold text-action">
              Zobacz historię uruchomień
            </a>
          </div>
        </article>

        <article className="rounded-md border border-line bg-white">
          <SystemPanelHeader title="Bezpieczeństwo" cta="Zobacz wszystkie" href="/security" />
          <div className="divide-y divide-line">
            {systemSecurityRows().map((row) => (
              <SystemListRow
                key={row.title}
                title={row.title}
                description={row.description}
                status={row.status === "active" ? "aktywna" : "zablokowana"}
                statusClass={row.status === "active" ? "bg-success/10 text-success" : "bg-risk/10 text-risk"}
              />
            ))}
          </div>
          <div className="border-t border-line px-4 py-3">
            <a href="/security" className="text-sm font-semibold text-action">
              Zobacz reguły bezpieczeństwa
            </a>
          </div>
        </article>
      </section>

      <section className="rounded-md border border-line bg-white">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-base font-semibold text-ink">Eksperymentalne obszary</h2>
          <p className="mt-1 text-sm text-slate-600">
            Obszary w fazie testów lub z ograniczonym dostępem.
          </p>
        </div>
        <div className="grid gap-3 p-4 xl:grid-cols-2">
          <SystemExperimentCard
            title="Posty społecznościowe"
            status="w review"
            description="Publikacja i harmonogram treści w social media."
            note="Obszar w weryfikacji. Trwają testy integracji i zasad odpowiedzialności."
          />
          <SystemExperimentCard
            title="Eksporty Google Sheets"
            status="zablokowany"
            description="Eksport danych i raportów do arkuszy Google."
            note="Nie spełnia standardów bezpieczeństwa. Eksporty zewnętrzne wyłączone."
            blocked
          />
        </div>
      </section>

      <section className="rounded-md border border-line bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
          <div>
            <h2 className="text-base font-semibold text-ink">Szczegóły techniczne</h2>
            <p className="mt-1 text-sm text-slate-600">
              Podstawowe informacje systemowe i dostępność.
            </p>
          </div>
          <a
            href="/settings"
            className="rounded-md border border-action/30 px-4 py-2 text-sm font-semibold text-action"
          >
            Zobacz szczegóły techniczne
          </a>
        </div>
        <div className="grid divide-y divide-line text-sm md:grid-cols-2 md:divide-x md:divide-y-0">
          <div className="grid divide-y divide-line">
            <SystemDetailRow label="Adaptery" value={`${activeConnectors} aktywnych`} />
            <SystemDetailRow label="Logi" value="ostatnie uruchomienia dostępne w audycie" />
          </div>
          <div className="grid divide-y divide-line">
            <SystemDetailRow label="Runtime" value="lokalny WILQ API i dashboard" />
            <SystemDetailRow label="Role" value="marketer mode + technical audit mode" />
          </div>
        </div>
      </section>
    </>
  );
}

function SystemPanelHeader({ title, cta, href }: { title: string; cta: string; href: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      <a href={href} className="rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-action">
        {cta}
      </a>
    </div>
  );
}

function SystemListRow({
  title,
  description,
  status,
  statusClass
}: {
  title: string;
  description: string;
  status: string;
  statusClass: string;
}) {
  return (
    <div className="flex items-start justify-between gap-3 px-4 py-3">
      <div>
        <div className="text-sm font-semibold text-ink">{title}</div>
        <p className="mt-1 line-clamp-2 text-sm leading-6 text-slate-600">{description}</p>
      </div>
      <span className={`shrink-0 rounded px-2 py-1 text-xs font-semibold ${statusClass}`}>
        {status}
      </span>
    </div>
  );
}

function SystemExperimentCard({
  title,
  status,
  description,
  note,
  blocked = false
}: {
  title: string;
  status: string;
  description: string;
  note: string;
  blocked?: boolean;
}) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
        </div>
        <span className={`rounded px-2 py-1 text-xs font-semibold ${blocked ? "bg-risk/10 text-risk" : "bg-wait/10 text-wait"}`}>
          {status}
        </span>
      </div>
      <p className={`mt-4 rounded-md border p-3 text-sm leading-6 ${
        blocked
          ? "border-risk/30 bg-risk/10 text-risk"
          : "border-action/30 bg-action/5 text-slate-700"
      }`}
      >
        {note}
      </p>
    </article>
  );
}

function SystemDetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[160px_1fr] gap-3 px-4 py-3">
      <div className="font-semibold text-ink">{label}</div>
      <div className="text-slate-600">{value}</div>
    </div>
  );
}

function systemSecurityRows() {
  return [
    {
      title: "Brak zapisu zmian bez audytu",
      description: "Zmiany zapisywane tylko po audycie.",
      status: "active"
    },
    {
      title: "Brak rekomendacji bez dowodów",
      description: "Rekomendacje muszą mieć dowody.",
      status: "active"
    },
    {
      title: "Zapis zmian zawsze z dowodami",
      description: "Każdy zapis wymaga źródeł i uzasadnienia.",
      status: "active"
    },
    {
      title: "Blokada bez kontekstu",
      description: "Blokada bez wyjaśnienia jest zabroniona.",
      status: "active"
    },
    {
      title: "Brak pobrań z kontekstem",
      description: "WILQ nie może pobrać Social Context-Pack.",
      status: "blocked"
    }
  ] as const;
}

function formatSystemRunDescription(run: WorkflowRun) {
  const timestamp = new Date(run.started_at).toLocaleString("pl-PL", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  });
  return `${timestamp} · Operator: System`;
}

function KnowledgeSurfaceSections({
  knowledgeMap,
  knowledgeCards,
  playbooks,
  showKnowledgeMap,
  setShowKnowledgeMap,
  showKnowledgeCards,
  setShowKnowledgeCards,
  showKnowledgePlaybooks,
  setShowKnowledgePlaybooks
}: {
  knowledgeMap: UseQueryResult<KnowledgeOperatingMapResponse>;
  knowledgeCards: UseQueryResult<KnowledgeCard[]>;
  playbooks: UseQueryResult<MarketingPlaybook[]>;
  showKnowledgeMap: boolean;
  setShowKnowledgeMap: (value: boolean | ((current: boolean) => boolean)) => void;
  showKnowledgeCards: boolean;
  setShowKnowledgeCards: (value: boolean | ((current: boolean) => boolean)) => void;
  showKnowledgePlaybooks: boolean;
  setShowKnowledgePlaybooks: (value: boolean | ((current: boolean) => boolean)) => void;
}) {
  const map = knowledgeMap.data;
  const cards = knowledgeCards.data ?? [];
  const bindings = map?.bindings ?? [];
  const nearestCard = cards[0];
  const nearestTitle =
    nearestCard?.display_title || nearestCard?.title || bindings[0]?.title || "Karta wiedzy do review";
  const blockedClaimCount = bindings.reduce(
    (sum, binding) => sum + binding.blocked_claim_labels.length,
    0
  );
  const reviewCount = Math.max(
    cards.length + bindings.filter((binding) => binding.has_blocked_claims || binding.has_missing_contracts).length,
    0
  );
  const allowedClaimCount = Math.max(0, bindings.length * 3 - blockedClaimCount);
  const reviewClaimCount = Math.max(reviewCount, bindings.length);
  const totalClaims = Math.max(allowedClaimCount + reviewClaimCount + blockedClaimCount, 1);
  const serviceCount = cards.filter((card) => /service|usług|usl|service_profile/i.test(card.card_type)).length;
  const approvedCurrentCount = 0;

  return (
    <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KnowledgeStatTile value={cards.length} label="kart" cta="Zobacz wszystkie" />
        <KnowledgeStatTile value={serviceCount} label="usług" cta="Zobacz wszystkie" tone="success" />
        <KnowledgeStatTile value={reviewCount} label="do sprawdzenia" cta="Przejdź do kolejki" tone="wait" />
        <KnowledgeStatTile value={approvedCurrentCount} label="zatwierdzonych" cta="Zobacz zatwierdzone" tone="action" />
      </section>
      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-md border border-line bg-white">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold text-ink">Najbliższa wiedza do sprawdzenia</h2>
            <span className="rounded bg-wait/10 px-2 py-1 text-xs font-semibold text-wait">
              Wymaga sprawdzenia
            </span>
          </div>
          <div className="p-4">
            <h3 className="text-base font-semibold text-ink">
              Sprawdź kartę: {nearestTitle}
            </h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-700">
              Karta ma źródła, ale wymaga decyzji człowieka zanim stanie się
              zatwierdzoną wiedzą produkcyjną.
            </p>
            <div className="mt-4">
              <div className="text-sm font-semibold text-ink">Wymagane sprawdzenia</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {[
                  "decyzja właściciela",
                  "źródła są jasne",
                  "twierdzenia sprawdzone",
                  "notatka z decyzji"
                ].map((label) => (
                  <span
                    key={label}
                    className="rounded border border-line bg-slate-50 px-2 py-1 text-xs text-slate-700"
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <a
                href="#knowledge-review-queue"
                className="inline-flex rounded-md bg-action px-4 py-2 text-sm font-semibold text-white"
              >
                Sprawdź kartę
              </a>
              <button
                type="button"
                className="rounded-md border border-action/30 px-4 py-2 text-sm font-semibold text-action"
                onClick={() => setShowKnowledgeCards((value) => !value)}
              >
                Pokaż kartę
              </button>
            </div>
          </div>
        </article>
        <article className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold text-ink">Co blokuje produkcję treści</h2>
          </div>
          <div className="divide-y divide-line">
            <KnowledgeBlockerRow
              title="Brak zatwierdzenia człowieka"
              description="Karty i propozycje treści wymagają sprawdzenia przed użyciem jako wiedza produkcyjna."
            />
            <KnowledgeBlockerRow
              title="Zablokowane twierdzenia"
              description={
                blockedClaimCount > 0
                  ? `${blockedClaimCount} twierdzeń wymaga blokady albo ręcznego przeglądu.`
                  : "Część twierdzeń może być niepełna, prywatna albo bez jasnego źródła."
              }
            />
            <KnowledgeBlockerRow
              title="Wymagane review"
              description="Publiczne i prywatne źródła Ekologus wymagają oceny człowieka przed użyciem w treściach."
            />
          </div>
          <div className="border-t border-line px-4 py-3">
            <button
              type="button"
              className="text-sm font-semibold text-action"
              onClick={() => setShowKnowledgePlaybooks((value) => !value)}
            >
              Zobacz pełne zasady pracy
            </button>
          </div>
        </article>
      </section>
      <section className="grid gap-4 xl:grid-cols-[1fr_280px]">
        <article id="knowledge-review-queue" className="rounded-md border border-line bg-white">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold text-ink">Kolejka sprawdzania wiedzy</h2>
            <button
              type="button"
              className="text-sm font-semibold text-action"
              onClick={() => setShowKnowledgeMap((value) => !value)}
            >
              Zobacz pełną kolejkę
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-semibold">Typ</th>
                  <th className="px-4 py-3 font-semibold">Karta</th>
                  <th className="px-4 py-3 font-semibold">Źródło</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Następny krok</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {knowledgeReviewRows(cards, bindings).map((row) => (
                  <tr key={row.id}>
                    <td className="px-4 py-3 font-medium text-action">{row.type}</td>
                    <td className="px-4 py-3 text-slate-700">{row.title}</td>
                    <td className="px-4 py-3 text-slate-600">{row.source}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded px-2 py-1 text-xs font-semibold ${row.statusClass}`}>
                        {row.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{row.nextStep}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
        <article className="rounded-md border border-line bg-white p-4">
          <h2 className="text-base font-semibold text-ink">Status twierdzeń</h2>
          <div className="mt-4 grid gap-4">
            <ClaimStatusBar
              label="Dozwolone"
              value={allowedClaimCount}
              total={totalClaims}
              className="bg-success"
            />
            <ClaimStatusBar
              label="Wymaga review"
              value={reviewClaimCount}
              total={totalClaims}
              className="bg-wait"
            />
            <ClaimStatusBar
              label="Zakazane"
              value={blockedClaimCount}
              total={totalClaims}
              className="bg-risk"
            />
            <div className="border-t border-line pt-3 text-sm font-semibold text-ink">
              Łącznie {totalClaims}
            </div>
          </div>
        </article>
      </section>
      <section className="rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-ink">Brak osobnego etapu przygotowania.</h2>
            <p className="mt-1 text-sm leading-6 text-slate-700">
              Fakty trafiają do wiedzy produkcyjnej dopiero po decyzji człowieka.
              Każda decyzja jest rejestrowana i możliwa do sprawdzenia.
            </p>
          </div>
          <button
            type="button"
            className="rounded-md border border-action/30 px-4 py-2 text-sm font-semibold text-action"
            onClick={() => setShowKnowledgePlaybooks((value) => !value)}
          >
            Zasady pracy z wiedzą
          </button>
        </div>
      </section>
      {knowledgeMap.isLoading || knowledgeCards.isLoading || playbooks.isLoading ? (
        <section>
          <LoadingBand />
        </section>
      ) : null}
      {knowledgeMap.error || knowledgeCards.error || playbooks.error ? (
        <InlineErrorState message="Nie udało się pobrać pełnej wiedzy. Nie traktuj tego widoku jako gotowego do review." />
      ) : null}
      {showKnowledgeMap ? (
        <section>
          <SectionHeading title="Pełna mapa wiedzy" />
          <KnowledgeMapDetails mapQuery={knowledgeMap} />
        </section>
      ) : null}
      {showKnowledgeCards ? (
        <section>
          <SectionHeading title="Karty wiedzy" />
          <KnowledgeCardsDetails cardsQuery={knowledgeCards} />
        </section>
      ) : null}
      {showKnowledgePlaybooks ? (
        <section>
          <SectionHeading title="Zasady pracy" />
          <KnowledgePlaybooksDetails playbooksQuery={playbooks} />
        </section>
      ) : null}
    </>
  );
}

function KnowledgeStatTile({
  value,
  label,
  cta,
  tone = "default"
}: {
  value: number;
  label: string;
  cta: string;
  tone?: "default" | "success" | "wait" | "action";
}) {
  const toneClass =
    tone === "success"
      ? "bg-success/10 text-success"
      : tone === "wait"
        ? "bg-wait/10 text-wait"
        : tone === "action"
          ? "bg-action/10 text-action"
          : "bg-action/10 text-action";
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex items-center gap-4">
        <div className={`flex h-11 w-11 items-center justify-center rounded-full ${toneClass}`}>
          <ShieldCheck size={20} aria-hidden="true" />
        </div>
        <div>
          <div className="text-2xl font-semibold text-ink">{value}</div>
          <div className="text-sm text-slate-700">{label}</div>
        </div>
      </div>
      <div className="mt-4 text-sm font-semibold text-action">{cta}</div>
    </article>
  );
}

function KnowledgeBlockerRow({ title, description }: { title: string; description: string }) {
  return (
    <div className="px-4 py-3">
      <div className="font-semibold text-ink">{title}</div>
      <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
    </div>
  );
}

type KnowledgeReviewRow = {
  id: string;
  type: string;
  title: string;
  source: string;
  status: string;
  statusClass: string;
  nextStep: string;
};

function knowledgeReviewRows(
  cards: KnowledgeCard[],
  bindings: KnowledgeOperatingMapResponse["bindings"]
): KnowledgeReviewRow[] {
  const cardRows = cards.slice(0, 4).map((card) => ({
    id: `card-${card.id}`,
    type: card.card_type_label || card.card_type || "Karta",
    title: card.display_title || card.title,
    source: card.source_type_label || card.source_type,
    status: "Do review",
    statusClass: "bg-wait/10 text-wait",
    nextStep: "Przejdź do review"
  }));
  const bindingRows = bindings.slice(0, 4).map((binding) => ({
    id: `binding-${binding.id}`,
    type: binding.has_blocked_claims ? "Claim" : "Decyzja",
    title: binding.title,
    source: binding.source_connector_summary_label || "WILQ",
    status: binding.has_blocked_claims ? "Wymaga review" : "Do review",
    statusClass: binding.has_blocked_claims ? "bg-wait/10 text-wait" : "bg-success/10 text-success",
    nextStep: binding.next_step
  }));
  const blockedRows = bindings.flatMap((binding) =>
    binding.blocked_claim_labels.slice(0, 2).map((claim, index) => ({
      id: `claim-${binding.id}-${index}`,
      type: "Claim",
      title: claim,
      source: binding.title,
      status: "Zakazane",
      statusClass: "bg-risk/10 text-risk",
      nextStep: "Zobacz powód"
    }))
  );
  return [...cardRows, ...bindingRows, ...blockedRows].slice(0, 6);
}

function ClaimStatusBar({
  label,
  value,
  total,
  className
}: {
  label: string;
  value: number;
  total: number;
  className: string;
}) {
  const percentage = Math.round((value / total) * 100);
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-ink">{label}</span>
        <span className="font-semibold text-ink">
          {value} <span className="text-xs font-normal text-slate-500">{percentage}%</span>
        </span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${className}`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

function KnowledgeMapDetails({
  mapQuery
}: {
  mapQuery: UseQueryResult<KnowledgeOperatingMapResponse>;
}) {
  if (mapQuery.isLoading) return <LoadingBand />;
  if (mapQuery.error) {
    return <InlineErrorState message="Nie udało się pobrać pełnej mapy wiedzy." />;
  }
  if (!mapQuery.data) {
    return <InlineErrorState message="Mapa wiedzy nie zwróciła danych do pokazania." />;
  }
  return <KnowledgeOperatingMapPanel map={mapQuery.data} />;
}

function KnowledgeCardsDetails({
  cardsQuery
}: {
  cardsQuery: UseQueryResult<KnowledgeCard[]>;
}) {
  if (cardsQuery.isLoading) return <LoadingBand />;
  if (cardsQuery.error) {
    return <InlineErrorState message="Nie udało się pobrać kart wiedzy." />;
  }
  return <KnowledgeCardList cards={cardsQuery.data ?? []} />;
}

function KnowledgePlaybooksDetails({
  playbooksQuery
}: {
  playbooksQuery: UseQueryResult<MarketingPlaybook[]>;
}) {
  if (playbooksQuery.isLoading) return <LoadingBand />;
  if (playbooksQuery.error) {
    return <InlineErrorState message="Nie udało się pobrać playbooków wiedzy." />;
  }
  return <PlaybookList playbooks={playbooksQuery.data ?? []} />;
}

function SettingsSurfaceSections({ connectors }: { connectors: ConnectorStatus[] }) {
  const [showConnectorDetails, setShowConnectorDetails] = useState(false);
  const [refreshRunId, setRefreshRunId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const refreshMutation = useMutation({
    mutationFn: refreshConnector,
    onSuccess: (run) => {
      setRefreshRunId(run.id);
      void queryClient.invalidateQueries({ queryKey: ["connectors"] });
      void queryClient.invalidateQueries({ queryKey: ["command-center"] });
      void queryClient.invalidateQueries({ queryKey: ["ads-diagnostics"] });
      void queryClient.invalidateQueries({ queryKey: ["ga4-diagnostics"] });
      void queryClient.invalidateQueries({ queryKey: ["merchant-diagnostics"] });
      void queryClient.invalidateQueries({ queryKey: ["content-diagnostics"] });
    }
  });
  const refreshRunQuery = useQuery({
    queryKey: ["connector-refresh-run", refreshRunId],
    queryFn: () => getConnectorRefreshRun(refreshRunId as string),
    enabled: refreshRunId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 500 : false;
    }
  });
  const missing = connectors.filter((connector) => hasMissingSourceAccess(connector));
  const freshDailySources = connectors.filter(
    (connector) =>
      connector.active_for_daily_work
      && connector.configured
      && !hasMissingSourceAccess(connector)
      && !hasStaleSourceData(connector)
  );
  const staleDailySources = connectors.filter(hasStaleSourceData);
  const outsideDailyScope = connectors.filter((connector) => !connector.active_for_daily_work);
  const sourceImpactRows = buildSourceImpactRows(missing, staleDailySources, outsideDailyScope);

  if (connectors.length === 0) {
    return (
      <section>
        <BlockerNotice message="WILQ nie ma statusu źródeł danych; odśwież integracje przed oceną gotowości." />
      </section>
    );
  }

  return (
    <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SourceStatTile value={connectors.length} label="źródeł" tone="default" />
        <SourceStatTile value={freshDailySources.length} label="gotowe dziennie" tone="success" />
        <SourceStatTile value={missing.length} label="brak dostępu" tone="risk" />
        <SourceStatTile value={staleDailySources.length} label="wymagają odświeżenia" tone="wait" />
      </section>

      <section className="rounded-md border border-wait/40 bg-wait/10 p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-ink">Co blokuje pracę</h2>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
              {missing.length > 0
                ? `Brakuje dostępu do ${formatConnectorList(missing)}. WILQ może dalej używać skonfigurowanych źródeł, ale nie powinien opierać decyzji na danych z brakujących kanałów.`
                : "Braki dostępu nie blokują teraz głównej pracy."}
              {staleDailySources.length > 0
                ? ` ${staleDailySources.length} ${pluralize(
                    staleDailySources.length,
                    "źródło wymaga",
                    "źródła wymagają",
                    "źródeł wymaga"
                  )} odświeżenia przed oceną wyników.`
                : " Dane są gotowe do dziennej pracy po sprawdzeniu zakresu decyzji."}
            </p>
          </div>
          <a
            href="#source-impact"
            className="rounded-md border border-wait/40 bg-white px-4 py-2 text-sm font-semibold text-wait"
          >
            Zobacz szczegóły
          </a>
        </div>
      </section>

      <section className="rounded-md border border-line bg-white">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-base font-semibold text-ink">Dostęp do źródeł</h2>
        </div>
        <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-4">
          {connectors.map((connector) => (
            <SourceAccessCard
              key={connector.id}
              connector={connector}
              onRefresh={() => refreshMutation.mutate(connector.id)}
              refreshing={
                (refreshMutation.isPending && refreshMutation.variables === connector.id)
                || (refreshRunQuery.data?.connector_id === connector.id
                  && (refreshRunQuery.data.status === "queued"
                    || refreshRunQuery.data.status === "running"))
              }
              refreshError={
                refreshMutation.error && refreshMutation.variables === connector.id
                  ? refreshMutation.error
                  : null
              }
              refreshResult={
                refreshRunQuery.data?.connector_id === connector.id
                  ? refreshRunQuery.data
                  : refreshMutation.data?.connector_id === connector.id
                    ? refreshMutation.data
                  : null
              }
            />
          ))}
        </div>
      </section>

      <section id="source-impact" className="rounded-md border border-line bg-white">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-base font-semibold text-ink">Wpływ braków na decyzje</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
              <tr>
                <th className="px-4 py-3 font-semibold">Źródło</th>
                <th className="px-4 py-3 font-semibold">Co jest zablokowane</th>
                <th className="px-4 py-3 font-semibold">Wpływ na decyzje</th>
                <th className="px-4 py-3 font-semibold">Następny krok</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {sourceImpactRows.map((row) => (
                <tr key={row.id}>
                  <td className="px-4 py-3 font-medium text-ink">{row.source}</td>
                  <td className="px-4 py-3 text-slate-700">{row.blocked}</td>
                  <td className="px-4 py-3 text-slate-700">
                    <span className={`mr-2 inline-block h-2 w-2 rounded-full ${row.dotClass}`} />
                    {row.impact}
                  </td>
                  <td className="px-4 py-3 font-medium text-action">{row.nextStep}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-md border border-line bg-white p-4">
        <h2 className="text-base font-semibold text-ink">Eksport i pakiety</h2>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-4 rounded-md border border-action/30 bg-action/5 p-3">
          <p className="max-w-4xl text-sm leading-6 text-slate-700">
            Eksporty do Google Sheets są ograniczone do pakietów i zakresów bezpiecznych.
            Pełny eksport raportów i rejestru WILQ będzie dostępny po wdrożeniu zasad
            bezpiecznego eksportu.
          </p>
          <span className="rounded-md border border-wait/30 bg-white px-4 py-2 text-sm font-semibold text-wait">
            Eksport zablokowany
          </span>
        </div>
      </section>

      <section>
        <DetailToggle
          expanded={showConnectorDetails}
          label="Pokaż szczegóły techniczne źródeł"
          onClick={() => setShowConnectorDetails((value) => !value)}
        />
        {showConnectorDetails ? (
          <div className="mt-3">
            <ConnectorGrid connectors={connectors} />
          </div>
        ) : null}
      </section>
    </>
  );
}

function SourceStatTile({
  value,
  label,
  tone
}: {
  value: number;
  label: string;
  tone: "default" | "success" | "risk" | "wait";
}) {
  const toneClass =
    tone === "success"
      ? "bg-success/10 text-success"
      : tone === "risk"
        ? "bg-risk/10 text-risk"
        : tone === "wait"
          ? "bg-wait/10 text-wait"
          : "bg-action/10 text-action";
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex items-center gap-4">
        <div className={`flex h-11 w-11 items-center justify-center rounded-full ${toneClass}`}>
          <ShieldCheck size={20} aria-hidden="true" />
        </div>
        <div>
          <div className="text-2xl font-semibold text-ink">{value}</div>
          <div className="text-sm text-slate-700">{label}</div>
        </div>
      </div>
    </article>
  );
}

function SourceAccessCard({
  connector,
  onRefresh,
  refreshing,
  refreshError,
  refreshResult
}: {
  connector: ConnectorStatus;
  onRefresh: () => void;
  refreshing: boolean;
  refreshError: Error | null;
  refreshResult: ConnectorRefreshRun | null;
}) {
  const status = sourceAccessStatus(connector);
  const canRefresh = hasStaleSourceData(connector) && connector.refresh_state.refresh_allowed;
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">{connector.label}</h3>
          <p className="mt-2 text-xs leading-5 text-slate-600">
            {connector.product_scope_label || "Źródło danych sprawdzane przez WILQ."}
          </p>
        </div>
        <span className={`rounded px-2 py-1 text-xs font-semibold ${status.className}`}>
          {status.label}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">
        {status.description}
      </p>
      <div className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
        <span className="font-semibold text-ink">Stan odczytu: </span>
        {connector.refresh_state.state_label}. {connector.refresh_state.safe_next_step}
      </div>
      {canRefresh ? (
        <div className="mt-4 space-y-2">
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-md border border-wait/40 bg-white px-3 py-2 text-sm font-semibold text-wait disabled:cursor-wait disabled:opacity-70"
          >
            <RefreshCw
              size={15}
              aria-hidden="true"
              className={refreshing ? "animate-spin" : undefined}
            />
            {refreshing ? "Odświeżam dane" : "Odśwież dane"}
          </button>
          {refreshResult ? (
            <p className={`text-xs leading-5 ${refreshing ? "text-wait" : "text-success"}`}>
              {refreshing
                ? refreshResult.status_label || "Odczyt trwa; poczekaj na wynik."
                : refreshResult.status === "failed" || refreshResult.status === "blocked"
                  ? refreshResult.status_label || "Odczyt zablokowany; sprawdź dostęp."
                  : "Odczyt zakończony. WILQ odświeży decyzje po aktualizacji źródła."}
            </p>
          ) : null}
          {refreshError ? (
            <p className="text-xs leading-5 text-risk">
              Nie udało się odświeżyć źródła. Sprawdź dostęp lub spróbuj ponownie.
            </p>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

function sourceAccessStatus(connector: ConnectorStatus) {
  if (hasMissingSourceAccess(connector)) {
    return {
      label: "Brak dostępu",
      className: "bg-risk/10 text-risk",
      description: "Dostęp wymaga uzupełnienia przed decyzjami z tego kanału."
    };
  }
  if (!connector.active_for_daily_work) {
    return {
      label: "Poza zakresem",
      className: "bg-wait/10 text-wait",
      description: "Dane nie są liczone do głównego dziennego zakresu pracy."
    };
  }
  if (hasStaleSourceData(connector)) {
    return {
      label: "Do odświeżenia",
      className: "bg-wait/10 text-wait",
      description: "Dane są dostępne, ale nie powinny domykać decyzji bez świeżego odczytu."
    };
  }
  if (connector.configured) {
    return {
      label: "Aktywny",
      className: "bg-success/10 text-success",
      description: "Dane dostępne i aktualizowane przez WILQ."
    };
  }
  return {
    label: connector.status_label || "Do sprawdzenia",
    className: "bg-wait/10 text-wait",
    description: "Status wymaga sprawdzenia przed użyciem w decyzjach."
  };
}

function hasMissingSourceAccess(connector: ConnectorStatus) {
  return connector.missing_credentials.length > 0 || connector.status === "missing_credentials";
}

function hasStaleSourceData(connector: ConnectorStatus) {
  return (
    connector.active_for_daily_work
    && connector.configured
    && !hasMissingSourceAccess(connector)
    && connector.freshness.state === "stale"
  );
}

type SourceImpactRow = {
  id: string;
  source: string;
  blocked: string;
  impact: string;
  nextStep: string;
  dotClass: string;
};

function buildSourceImpactRows(
  missing: ConnectorStatus[],
  stale: ConnectorStatus[],
  outsideDailyScope: ConnectorStatus[]
): SourceImpactRow[] {
  const missingRows = missing.map((connector) => ({
    id: `missing-${connector.id}`,
    source: connector.label,
    blocked: sourceBlockedDecisionLabel(connector),
    impact: sourceDecisionImpactLabel(connector),
    nextStep: sourceRepairStepLabel(connector),
    dotClass: "bg-risk"
  }));
  const staleRows = stale.map((connector) => ({
    id: `stale-${connector.id}`,
    source: connector.label,
    blocked: sourceStaleDecisionLabel(connector),
    impact: "Decyzja wymaga świeżego odczytu przed wnioskiem",
    nextStep: "Odśwież źródło przed decyzją",
    dotClass: "bg-wait"
  }));
  const outsideRow =
    outsideDailyScope.length > 0
      ? [
          {
            id: "outside-daily-scope",
            source: "Inne poza zakresem",
            blocked: `Dane z ${outsideDailyScope.length} ${pluralize(
              outsideDailyScope.length,
              "źródła",
              "źródeł",
              "źródeł"
            )} pomijane w dziennym zakresie`,
            impact: "Ograniczony wgląd w nieujęte kanały",
            nextStep: "Zostaw poza planem dnia albo włącz zakres",
            dotClass: "bg-wait"
          }
        ]
      : [];
  if (missingRows.length === 0 && staleRows.length === 0 && outsideRow.length === 0) {
    return [
      {
        id: "sources-ready",
        source: "Brak krytycznych braków",
        blocked: "Główne źródła mogą zasilać decyzje po sprawdzeniu świeżości danych",
        impact: "Decyzje nie są blokowane przez dostęp",
        nextStep: "Pracuj dalej i pilnuj świeżości",
        dotClass: "bg-success"
      }
    ];
  }
  return [...missingRows, ...staleRows, ...outsideRow];
}

function sourceBlockedDecisionLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  const label = connector.label;
  if (id.includes("linkedin")) return "Reklamy LinkedIn, zasięgi, zaangażowanie, leady";
  if (id.includes("facebook")) return "Posty, zasięgi, zaangażowanie, wyniki kampanii";
  if (id.includes("google_ads")) return "Kampanie, rekomendacje, search terms i bezpieczne akcje Ads";
  if (id.includes("analytics") || id.includes("ga4")) return "Ocena jakości ruchu, konwersji i zdarzeń";
  if (id.includes("merchant")) return "Feed produktowy, status produktów i widoczność Shopping/PMax";
  if (id.includes("wordpress")) return "Treści, publikacje i sprawdzenie istniejących stron";
  return `${label}: decyzje zależne od tego źródła`;
}

function sourceDecisionImpactLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  if (id.includes("linkedin")) return "Brak pełnego obrazu działań w kanałach B2B";
  if (id.includes("facebook")) return "Niepełna ocena skuteczności komunikacji";
  if (id.includes("google_ads")) return "Blokada pełnej oceny Ads i zmian kampanii";
  if (id.includes("analytics") || id.includes("ga4")) return "Nie wolno oceniać efektu kampanii bez pomiaru";
  if (id.includes("merchant")) return "Nie wolno oceniać gotowości produktów bez danych pliku produktowego";
  if (id.includes("wordpress")) return "Ryzyko duplikacji i pracy na nieaktualnym spisie treści";
  return "Decyzje z tego kanału pozostają zablokowane albo zdegradowane";
}

function sourceRepairStepLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  if (id.includes("linkedin")) return "Podłącz LinkedIn albo zostaw social jako review-only";
  if (id.includes("facebook")) return "Podłącz Facebook Pages albo pomiń ten kanał";
  if (id.includes("google_ads")) return "Uzupełnij dostęp Ads i odśwież źródło";
  if (id.includes("analytics") || id.includes("ga4")) return "Uzupełnij GA4 i sprawdź pomiar";
  if (id.includes("merchant")) return "Uzupełnij Merchant i odśwież feed";
  if (id.includes("wordpress")) return "Uzupełnij WordPress i pobierz spis treści";
  return "Uzupełnij dostęp i odśwież źródło";
}

function sourceStaleDecisionLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  if (id.includes("google_ads")) return "Aktualna ocena kampanii, kosztów i rekomendacji";
  if (id.includes("analytics") || id.includes("ga4")) return "Aktualna ocena jakości ruchu i pomiaru";
  if (id.includes("merchant")) return "Aktualny status pliku produktowego, produktów i atrybutów";
  if (id.includes("search_console")) return "Aktualne decyzje SEO z GSC";
  if (id.includes("wordpress")) return "Aktualny spis treści i ryzyko duplikacji";
  if (id.includes("ahrefs")) return "Aktualne luki SEO i konkurencja";
  if (id.includes("localo")) return "Aktualna widoczność lokalna";
  return `${connector.label}: decyzje wymagają świeżego odczytu`;
}

function formatConnectorList(connectors: ConnectorStatus[]) {
  if (connectors.length === 1) return connectors[0].label;
  if (connectors.length === 2) return `${connectors[0].label} i ${connectors[1].label}`;
  return `${connectors.slice(0, -1).map((connector) => connector.label).join(", ")} i ${
    connectors[connectors.length - 1].label
  }`;
}

function pluralize(count: number, one: string, few: string, many: string) {
  if (count === 1) return one;
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return few;
  return many;
}

function SectionHeading({ title }: { title: string }) {
  return <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-slate-600">{title}</h2>;
}

function DetailToggle({
  expanded,
  label,
  onClick
}: {
  expanded: boolean;
  label: string;
  onClick: () => void;
}) {
  const Icon = expanded ? ChevronDown : ChevronRight;
  return (
    <button
      type="button"
      aria-expanded={expanded}
      onClick={onClick}
      className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
    >
      <Icon aria-hidden="true" size={16} />
      {label}
    </button>
  );
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
