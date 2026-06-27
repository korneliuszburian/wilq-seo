import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, FileJson, ShieldCheck } from "lucide-react";
import { useState } from "react";

import {
  getConnectors,
  getKnowledgeCards,
  getKnowledgeOperatingMap,
  getKnowledgePlaybooks,
  getWorkflowRuns,
  getWorkflows,
  type ConnectorStatus
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
  const isKnowledgeRoute = routeName.startsWith("/knowledge");
  const [showKnowledgeMap, setShowKnowledgeMap] = useState(false);
  const [showKnowledgeCards, setShowKnowledgeCards] = useState(false);
  const [showKnowledgePlaybooks, setShowKnowledgePlaybooks] = useState(false);
  const [showConnectorDetails, setShowConnectorDetails] = useState(false);
  const isWorkflowRoute = routeName.startsWith("/workflows");
  const isSettingsRoute = routeName.startsWith("/settings");
  const compactRoute = compactRouteConfig(routeName);
  const shouldLoadConnectorStatus = isSettingsRoute;
  const connectors = useQuery({
    queryKey: ["connectors"],
    queryFn: getConnectors,
    enabled: shouldLoadConnectorStatus
  });
  const workflows = useQuery({
    queryKey: ["workflows"],
    queryFn: getWorkflows,
    enabled: isWorkflowRoute
  });
  const workflowRuns = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: getWorkflowRuns,
    enabled: isWorkflowRoute
  });
  const knowledgeMap = useQuery({
    queryKey: ["knowledge-operating-map"],
    queryFn: getKnowledgeOperatingMap,
    enabled: isKnowledgeRoute
  });
  const knowledgeCards = useQuery({
    queryKey: ["knowledge-cards"],
    queryFn: getKnowledgeCards,
    enabled: isKnowledgeRoute
  });
  const playbooks = useQuery({
    queryKey: ["knowledge-playbooks"],
    queryFn: getKnowledgePlaybooks,
    enabled: isKnowledgeRoute
  });
  const isWorkflowLoading = isWorkflowRoute && (workflows.isLoading || workflowRuns.isLoading);
  const hasWorkflowError = isWorkflowRoute && (workflows.error || workflowRuns.error);
  if (
    connectors.isLoading ||
    isWorkflowLoading
  ) {
    return <LoadingBand />;
  }
  if (
    connectors.error ||
    hasWorkflowError
  ) {
    return <ErrorState />;
  }

  const title = isKnowledgeRoute
    ? "Baza wiedzy WILQ"
    : isSettingsRoute
      ? "Ustawienia"
      : compactRoute
        ? compactRoute.title
        : "Widok WILQ";
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{title || "Centrum pracy"}</h1>
          <p className="mt-1 text-sm text-slate-600">
            {isKnowledgeRoute
              ? "Wiedza używana tylko wtedy, gdy wpływa na decyzję, blokadę albo następny bezpieczny krok."
              : isSettingsRoute
                ? "Status dostępu do źródeł WILQ. Braki dostępu pokazujemy bez wartości sekretów."
              : "Powierzchnia WILQ z dowodami, źródłami danych i stanem akcji."}
          </p>
        </div>
        <FileJson aria-hidden="true" className="text-action" size={28} />
      </div>
      <div className="grid gap-6">
        {isWorkflowRoute ? (
          <>
            <section>
              <SectionHeading title="Procesy decyzyjne" />
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {(workflows.data ?? []).map((workflow) => (
                  <article key={workflow.id} className="rounded-md border border-line bg-white p-4">
                    <h3 className="text-sm font-semibold">{workflow.label}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{workflow.description}</p>
                  </article>
                ))}
              </div>
            </section>
            <section>
              <SectionHeading title="Ostatnie uruchomienia" />
              <WorkflowRunList runs={workflowRuns.data ?? []} />
            </section>
          </>
        ) : null}
        {isKnowledgeRoute ? (
          <>
            <section>
              <SectionHeading title="Co ta wiedza zmienia w decyzjach" />
              {knowledgeMap.isLoading ? (
                <LoadingBand />
              ) : knowledgeMap.error ? (
                <InlineErrorState message="Nie udało się pobrać mapy wiedzy do decyzji." />
              ) : (
                <KnowledgeDecisionImpactPanel
                  map={
                    knowledgeMap.data ?? {
                      generated_at: "",
                      source_card_count: 0,
                      playbook_count: 0,
                      expert_rule_count: 0,
                      binding_count: 0,
                      bindings: []
                    }
                  }
                />
              )}
            </section>
            <section>
              <DetailToggle
                expanded={showKnowledgeMap}
                label="Pokaż pełną mapę wiedzy"
                onClick={() => setShowKnowledgeMap((value) => !value)}
              />
              {showKnowledgeMap ? (
                knowledgeMap.isLoading ? (
                  <LoadingBand />
                ) : knowledgeMap.error ? (
                  <InlineErrorState message="Nie udało się pobrać pełnej mapy wiedzy." />
                ) : (
                  <KnowledgeOperatingMapPanel
                    map={
                      knowledgeMap.data ?? {
                        generated_at: "",
                        source_card_count: 0,
                        playbook_count: 0,
                        expert_rule_count: 0,
                        binding_count: 0,
                        bindings: []
                      }
                    }
                  />
                )
              ) : null}
            </section>
            <section>
              <DetailToggle
                expanded={showKnowledgeCards}
                label="Pokaż źródła wiedzy"
                onClick={() => setShowKnowledgeCards((value) => !value)}
              />
              {showKnowledgeCards ? (
                knowledgeCards.isLoading ? (
                  <LoadingBand />
                ) : knowledgeCards.error ? (
                  <InlineErrorState message="Nie udało się pobrać kart wiedzy." />
                ) : (
                  <KnowledgeCardList cards={knowledgeCards.data ?? []} />
                )
              ) : null}
            </section>
            <section>
              <DetailToggle
                expanded={showKnowledgePlaybooks}
                label="Pokaż zasady pracy"
                onClick={() => setShowKnowledgePlaybooks((value) => !value)}
              />
              {showKnowledgePlaybooks ? (
                playbooks.isLoading ? (
                  <LoadingBand />
                ) : playbooks.error ? (
                  <InlineErrorState message="Nie udało się pobrać playbooków wiedzy." />
                ) : (
                  <PlaybookList playbooks={playbooks.data ?? []} />
                )
              ) : null}
            </section>
          </>
        ) : null}
        {isSettingsRoute ? (
          <section>
            <SectionHeading title="Dostęp do źródeł danych" />
            <ConnectorAccessSummary connectors={connectors.data ?? []} />
            <div className="mt-4">
              <DetailToggle
                expanded={showConnectorDetails}
                label="Pokaż stan dostępu"
                onClick={() => setShowConnectorDetails((value) => !value)}
              />
              {showConnectorDetails ? (
                <div className="mt-3">
                  <ConnectorGrid connectors={connectors.data ?? []} />
                </div>
              ) : null}
            </div>
          </section>
        ) : null}
        {compactRoute ? <CompactRoutePanel config={compactRoute} /> : null}
      </div>
    </main>
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
      "Skrót obszaru, który docelowo ma pokazywać realne treści z ekologus.pl i sklepu. Dziś decyzje contentowe są prowadzone w Content Plannerze.",
    status: "w trakcie porządkowania",
    nextStep: "Przejdź do Content Plannera i sprawdź kolejkę zachowania, odświeżenia, scalenia albo blokady.",
    blockers: [
      "pełny Content Inventory v2 nie jest jeszcze gotowy",
      "brak finalnego preflightu duplikacji i kanonicznych URL-i"
    ],
    safeRoute: "/content-planner"
  },
  "/google-sheets": {
    title: "Google Sheets",
    description:
      "Miejsce na eksporty i pakiety do pracy operacyjnej. Ten widok nie powinien udawać raportu ani pokazywać pełnego rejestru WILQ.",
    status: "zablokowane do czasu kontraktu eksportu",
    nextStep:
      "Najpierw wybierz konkretny zakres eksportu: pakiet UAT, lista decyzji, kolejka treści albo dowody do sprawdzenia.",
    blockers: [
      "brak zatwierdzonego zakresu eksportu",
      "brak reguł, które pola mogą trafić do arkusza bez sekretów i technicznych śladów"
    ],
    safeRoute: "/command-center"
  },
  "/codex-runs": {
    title: "Uruchomienia Codex",
    description:
      "Miejsce na historię pracy operatora i skill evale. Domyślny widok nie pokazuje surowych promptów ani pełnych danych technicznych.",
    status: "częściowo dostępne przez proofy i eval ledger",
    nextStep:
      "Sprawdź `docs/PROGRESS.md` i `docs/evals/skill-eval-ledger.md`, jeśli potrzebujesz dowodu ostatniego przebiegu.",
    blockers: [
      "brak osobnego widoku historii uruchomień z redakcją surowych promptów",
      "brak finalnego podziału na proof użytkowy i widok techniczny operatora"
    ]
  },
  "/security": {
    title: "Bezpieczeństwo",
    description:
      "Kontrola zasad bezpieczeństwa WILQ: brak sekretów w UI, brak zapisu zmian bez audytu i brak rekomendacji bez dowodów.",
    status: "zasady aktywne, widok produktowy do dopracowania",
    nextStep:
      "Do weryfikacji użyj aktualnych testów redakcji, action gates i proofów w `docs/PROGRESS.md`.",
    blockers: [
      "brak pełnego dashboardu bezpieczeństwa",
      "brak produkcyjnych ról i uprawnień"
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
    return <BlockerNotice message="Brak statusu źródeł danych w WILQ." />;
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
              <StatusBadge value={connector.status} />
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
        <MetricTile label="Rejestry techniczne" value="schowane" />
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
