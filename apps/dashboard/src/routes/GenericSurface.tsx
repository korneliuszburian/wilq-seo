import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, FileJson, ShieldCheck } from "lucide-react";
import { useState } from "react";

import {
  getConnectors,
  getKnowledgeCards,
  getKnowledgeOperatingMap,
  getKnowledgePlaybooks,
  getWorkflowRuns,
  getWorkflows,
  type ConnectorStatus,
  type KnowledgeCard,
  type KnowledgeOperatingMapResponse,
  type MarketingPlaybook,
  type Workflow,
  type WorkflowRun
} from "../lib/api";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import {
  KnowledgeCardList,
  KnowledgeDecisionImpactPanel,
  KnowledgeOperatingMapPanel,
  PlaybookList
} from "./KnowledgePanels";
import { ConnectorGrid } from "./RegistryPanels";
import { WorkflowRunList } from "./WorkflowPanels";

export function GenericSurface({ routeName }: { routeName: string }) {
  const compactRoute = compactRouteConfig(routeName);
  const routeKind = genericRouteKind(routeName, compactRoute);
  const connectors = useQuery({
    queryKey: ["connectors"],
    queryFn: getConnectors,
    enabled: routeKind === "settings"
  });
  const workflows = useQuery({
    queryKey: ["workflows"],
    queryFn: getWorkflows,
    enabled: routeKind === "workflow"
  });
  const workflowRuns = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: getWorkflowRuns,
    enabled: routeKind === "workflow"
  });
  const knowledgeMap = useQuery({
    queryKey: ["knowledge-operating-map"],
    queryFn: getKnowledgeOperatingMap,
    enabled: routeKind === "knowledge"
  });
  const knowledgeCards = useQuery({
    queryKey: ["knowledge-cards"],
    queryFn: getKnowledgeCards,
    enabled: routeKind === "knowledge"
  });
  const playbooks = useQuery({
    queryKey: ["knowledge-playbooks"],
    queryFn: getKnowledgePlaybooks,
    enabled: routeKind === "knowledge"
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
      />
    </main>
  );
}

type GenericRouteKind = "knowledge" | "workflow" | "settings" | "compact" | "generic";

function genericRouteKind(
  routeName: string,
  compactRoute: CompactRouteConfig | undefined
): GenericRouteKind {
  if (routeName.startsWith("/knowledge")) return "knowledge";
  if (routeName.startsWith("/workflows")) return "workflow";
  if (routeName.startsWith("/settings")) return "settings";
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
  if (routeKind === "workflow") return Boolean(workflows.error || workflowRuns.error);
  return false;
}

function genericSurfaceHeader(
  routeKind: GenericRouteKind,
  compactRoute: CompactRouteConfig | undefined
) {
  if (routeKind === "knowledge") {
    return {
      title: "Baza wiedzy WILQ",
      description:
        "Wiedza używana tylko wtedy, gdy wpływa na decyzję, blokadę albo następny bezpieczny krok."
    };
  }
  if (routeKind === "settings") {
    return {
      title: "Ustawienia",
      description: "Status dostępu do źródeł WILQ. Braki dostępu pokazujemy bez wartości sekretów."
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
  playbooks
}: {
  routeKind: GenericRouteKind;
  compactRoute: CompactRouteConfig | undefined;
  connectors: ConnectorStatus[];
  workflows: Workflow[];
  workflowRuns: WorkflowRun[];
  knowledgeMap: UseQueryResult<KnowledgeOperatingMapResponse>;
  knowledgeCards: UseQueryResult<KnowledgeCard[]>;
  playbooks: UseQueryResult<MarketingPlaybook[]>;
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
        />
      ) : null}
      {routeKind === "settings" ? <SettingsSurfaceSections connectors={connectors} /> : null}
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

function KnowledgeSurfaceSections({
  knowledgeMap,
  knowledgeCards,
  playbooks
}: {
  knowledgeMap: UseQueryResult<KnowledgeOperatingMapResponse>;
  knowledgeCards: UseQueryResult<KnowledgeCard[]>;
  playbooks: UseQueryResult<MarketingPlaybook[]>;
}) {
  const [showKnowledgeMap, setShowKnowledgeMap] = useState(false);
  const [showKnowledgeCards, setShowKnowledgeCards] = useState(false);
  const [showKnowledgePlaybooks, setShowKnowledgePlaybooks] = useState(false);

  return (
    <>
      <section>
        <SectionHeading title="Co ta wiedza zmienia w decyzjach" />
        <KnowledgeMapPreview mapQuery={knowledgeMap} />
      </section>
      <section>
        <DetailToggle
          expanded={showKnowledgeMap}
          label="Pokaż pełną mapę wiedzy"
          onClick={() => setShowKnowledgeMap((value) => !value)}
        />
        {showKnowledgeMap ? <KnowledgeMapDetails mapQuery={knowledgeMap} /> : null}
      </section>
      <section>
        <DetailToggle
          expanded={showKnowledgeCards}
          label="Pokaż źródła wiedzy"
          onClick={() => setShowKnowledgeCards((value) => !value)}
        />
        {showKnowledgeCards ? <KnowledgeCardsDetails cardsQuery={knowledgeCards} /> : null}
      </section>
      <section>
        <DetailToggle
          expanded={showKnowledgePlaybooks}
          label="Pokaż zasady pracy"
          onClick={() => setShowKnowledgePlaybooks((value) => !value)}
        />
        {showKnowledgePlaybooks ? <KnowledgePlaybooksDetails playbooksQuery={playbooks} /> : null}
      </section>
    </>
  );
}

function KnowledgeMapPreview({
  mapQuery
}: {
  mapQuery: UseQueryResult<KnowledgeOperatingMapResponse>;
}) {
  if (mapQuery.isLoading) return <LoadingBand />;
  if (mapQuery.error) {
    return <InlineErrorState message="Nie udało się pobrać mapy wiedzy do decyzji." />;
  }
  if (!mapQuery.data) {
    return <InlineErrorState message="Mapa wiedzy nie zwróciła danych do pokazania." />;
  }
  return <KnowledgeDecisionImpactPanel map={mapQuery.data} />;
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

  return (
    <section>
      <SectionHeading title="Dostęp do źródeł danych" />
      <ConnectorAccessSummary connectors={connectors} />
      <div className="mt-4">
        <DetailToggle
          expanded={showConnectorDetails}
          label="Pokaż stan dostępu"
          onClick={() => setShowConnectorDetails((value) => !value)}
        />
        {showConnectorDetails ? (
          <div className="mt-3">
            <ConnectorGrid connectors={connectors} />
          </div>
        ) : null}
      </div>
    </section>
  );
}

type CompactRouteConfig = {
  title: string;
  description: string;
  status: string;
  nextStep: string;
  blockers: string[];
  safeRoute?: string;
};

const COMPACT_ROUTE_CONFIGS: Record<string, CompactRouteConfig> = {
  "/content-inventory": {
    title: "Spis treści",
    description:
      "Skrót obszaru, który docelowo ma pokazywać realne treści z ekologus.pl i sklepu. Dziś decyzje treściowe są prowadzone w widoku treści.",
    status: "w trakcie porządkowania",
    nextStep: "Przejdź do widoku treści i sprawdź kolejkę zachowania, odświeżenia, scalenia albo blokady.",
    blockers: [
      "pełny spis treści nie jest jeszcze gotowy",
      "nie ma finalnego sprawdzenia duplikatów i adresów kanonicznych; nie używaj tego widoku do decyzji o pisaniu"
    ],
    safeRoute: "/content-planner"
  },
  "/google-sheets": {
    title: "Google Sheets",
    description:
      "Miejsce na eksporty i pakiety do pracy operacyjnej. Ten widok nie powinien udawać raportu ani pokazywać pełnego rejestru WILQ.",
    status: "zablokowane do czasu ustalenia bezpiecznego eksportu",
    nextStep:
      "Najpierw wybierz konkretny zakres eksportu: pakiet testowy, lista decyzji, kolejka treści albo dowody do sprawdzenia.",
    blockers: [
      "nie ma zatwierdzonego zakresu eksportu; nie wysyłaj danych poza WILQ",
      "nie ma reguł, które pola mogą trafić do arkusza bez sekretów i technicznych śladów"
    ],
    safeRoute: "/command-center"
  },
  "/codex-runs": {
    title: "Uruchomienia Codex",
    description:
      "Miejsce na historię pracy operatora i sprawdzenia jakości odpowiedzi. Domyślny widok nie pokazuje roboczych poleceń ani pełnych danych technicznych.",
    status: "częściowo dostępne przez zapisane wyniki sprawdzeń",
    nextStep:
      "Sprawdź ostatni zapis postępu, jeśli potrzebujesz potwierdzenia ostatniego przebiegu.",
    blockers: [
      "nie ma osobnego widoku historii uruchomień z oczyszczonymi poleceniami roboczymi",
      "nie ma finalnego podziału na potwierdzenie dla marketera i widok techniczny operatora"
    ]
  },
  "/security": {
    title: "Bezpieczeństwo",
    description:
      "Kontrola zasad bezpieczeństwa WILQ: brak sekretów w UI, brak zapisu zmian bez audytu i brak rekomendacji bez dowodów.",
    status: "zasady aktywne, widok produktowy do dopracowania",
    nextStep:
      "Do weryfikacji użyj aktualnych testów języka, blokad zapisu zmian i zapisanego postępu.",
    blockers: [
      "nie ma pełnego dashboardu bezpieczeństwa; traktuj ten widok jako skrót zasad",
      "nie ma produkcyjnych ról i uprawnień; nie traktuj tego jako modelu dostępu"
    ]
  }
};

function compactRouteConfig(routeName: string) {
  return COMPACT_ROUTE_CONFIGS[routeName];
}

function ConnectorAccessSummary({ connectors }: { connectors: ConnectorStatus[] }) {
  const configured = connectors.filter((connector) => connector.configured);
  const missing = connectors.filter((connector) => connector.missing_credentials.length > 0);
  const disabled = connectors.filter((connector) => connector.status === "disabled");

  if (connectors.length === 0) {
    return (
      <BlockerNotice message="WILQ nie ma statusu źródeł danych; odśwież integracje przed oceną gotowości." />
    );
  }

  return (
    <div className="grid gap-4">
      <div className="grid gap-2 text-center text-xs sm:grid-cols-4">
        <MetricTile label="Źródła" value={connectors.length} />
        <MetricTile label="Dostęp działa" value={configured.length} />
        <MetricTile label="Braki dostępu" value={missing.length} />
        <MetricTile label="Wyłączone" value={disabled.length} />
      </div>
      {missing.length > 0 ? (
        <article className="rounded-md border border-wait/30 bg-wait/10 p-4">
          <h3 className="text-sm font-semibold text-ink">Co blokuje pracę</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Brakuje dostępu do {formatConnectorList(missing)}. WILQ może dalej używać
            skonfigurowanych źródeł, ale nie powinien obiecywać wyników z brakujących kanałów.
          </p>
        </article>
      ) : (
        <article className="rounded-md border border-signal/30 bg-signal/10 p-4">
          <h3 className="text-sm font-semibold text-ink">Dostęp wygląda kompletnie</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Wszystkie znane źródła danych mają skonfigurowany dostęp. Nadal obowiązuje
            zasada: brak świeżych dowodów oznacza blokadę, nie domysł marketingowy.
          </p>
        </article>
      )}
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {connectors.map((connector) => (
          <article key={connector.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-sm font-semibold">{connector.label}</h3>
              <StatusBadge value={connector.status} label={connector.status_label} />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {connector.missing_credentials.length > 0
                ? `Wymaga uzupełnienia dostępu: ${connector.missing_credentials.length} ${pluralize(connector.missing_credentials.length, "pole", "pola", "pól")}.`
                : connector.configured
                  ? "Dostęp skonfigurowany. Szczegóły techniczne są dostępne po rozwinięciu."
                  : "Brak aktywnego dostępu. Szczegóły techniczne są dostępne po rozwinięciu."}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
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

function CompactRoutePanel({ config }: { config: CompactRouteConfig }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ShieldCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Status widoku
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">{config.description}</p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <MetricTile label="Status" value={config.status} />
        <MetricTile label="Blokady" value={config.blockers.length} />
        <MetricTile label="Szczegóły systemowe" value="schowane" />
      </div>
      <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-wait">
        <div className="font-semibold">Co zrobić dalej</div>
        <p>{config.nextStep}</p>
      </div>
      {config.blockers.length > 0 ? (
        <div className="mt-4 text-sm leading-6 text-slate-700">
          <div className="font-semibold text-ink">Co jeszcze blokuje gotowość</div>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {config.blockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {config.safeRoute ? (
        <a
          href={config.safeRoute}
          className="mt-4 inline-flex min-h-9 items-center rounded-md border border-action bg-white px-3 py-2 text-xs font-medium text-action hover:bg-action/10"
        >
          Otwórz bezpieczny widok
        </a>
      ) : null}
    </section>
  );
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
