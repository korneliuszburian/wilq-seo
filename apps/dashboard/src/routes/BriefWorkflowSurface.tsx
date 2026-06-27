import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import {
  getActions,
  getMarketingBrief,
  getTacticalQueue,
  MarketingBriefItem
} from "../lib/api";
import { MetricFactChips } from "../components/MetricFactChips";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import { ActionObjectFocus } from "./ActionObjectPanels";
import { TacticalQueuePanel } from "./TacticalQueuePanel";

export type BriefSurfaceConfig = {
  title: string;
  description: string;
  focusTitle: string;
  emptyMessage: string;
  safetyTitle: string;
  safetyText: string;
  connectorIds: string[];
  textNeedles: string[];
  showTacticalQueue?: boolean;
};

export const briefSurfaceConfigs: Record<string, BriefSurfaceConfig> = {
  "/ads-doctor": {
    title: "Google Ads",
    description:
      "Widok Google Ads oparty o WILQ. Pokazuje dowody, decyzje i twierdzenia, których nie wolno używać; jeśli Ads jest zablokowany, pokazuje blokadę zamiast diagnozy wydatków.",
    focusTitle: "Decyzje Ads",
    emptyMessage:
      "Brak dowodów Google Ads w WILQ. WILQ nie pokaże rekomendacji o wydatkach ani kampaniach bez odczytu Google Ads.",
    safetyTitle: "Brama bezpieczeństwa Ads",
    safetyText:
      "Zmiany kampanii, budżetu, wykluczeń i segmentów wymagają podglądu akcji, sprawdzenia w WILQ i audytu. Brak dowodów na zapytania, CPA albo zwrot z reklam oznacza zakres blokad, nie powód do zgadywania.",
    connectorIds: ["google_ads"],
    textNeedles: []
  },
  "/ga4": {
    title: "GA4",
    description:
      "Widok analityki zachowania i konwersji oparty o WILQ. Pokazuje tylko metryki GA4 z dowodami.",
    focusTitle: "Jakość ruchu GA4",
    emptyMessage:
      "Brak dowodów GA4 w WILQ. Uruchom odczyt GA4, zanim WILQ oceni strony wejścia albo jakość ruchu.",
    safetyTitle: "Brama bezpieczeństwa GA4",
    safetyText:
      "GA4 służy do diagnozy jakości ruchu i problemów pomiaru. WILQ nie traktuje braku danych jako spadku marketingowego bez dowodu źródłowego.",
    connectorIds: ["google_analytics_4"],
    textNeedles: []
  },
  "/localo": {
    title: "Localo",
    description:
      "Widok lokalnej widoczności oparty o gotowość WILQ i dowody Localo. Sam dostęp do źródła może działać, ale lokalne rekomendacje wymagają jeszcze konkretnych danych o rankingach i GBP.",
    focusTitle: "Lokalna widoczność do sprawdzenia",
    emptyMessage:
      "Brak konkretnych faktów Localo o rankingach i GBP w WILQ. WILQ może pokazać status dostępu, ale nie dopowiada lokalnych wyników bez dowodów.",
    safetyTitle: "Brama bezpieczeństwa lokalnej widoczności",
    safetyText:
      "Posty GBP i lokalne działania wymagają dowodów, podglądu akcji, sprawdzenia w WILQ i audytu. Sam dostęp do Localo nie zastępuje rankingów, wyniku GBP ani danych konkurencji.",
    connectorIds: ["localo"],
    textNeedles: [],
    showTacticalQueue: false
  },
  "/social-publisher": {
    title: "Publikacje social",
    description:
      "Widok publikacji social oparty o dowody WILQ i stan uprawnień. Przy brakach LinkedIn/Facebook pokazuje blokady, nie gotowe posty.",
    focusTitle: "Publikacje social do sprawdzenia",
    emptyMessage:
      "Brak dowodów social w WILQ. Uzupełnij dostęp LinkedIn/Facebook przed przygotowaniem propozycji postów.",
    safetyTitle: "Brama bezpieczeństwa publikacji",
    safetyText:
      "Posty LinkedIn/Facebook muszą bazować na claimach z dowodami i pozostać tylko do przygotowania, dopóki stan uprawnień, podgląd akcji i audyt nie są gotowe.",
    connectorIds: ["linkedin", "facebook"],
    textNeedles: []
  },
  "/content-planner": {
    title: "Treści",
    description:
      "Widok planowania treści łączy dowody GSC, GA4, Ahrefs, WordPress i Merchant w jedną kolejkę działań dla polskiego marketera.",
    focusTitle: "Priorytety treści do sprawdzenia",
    emptyMessage:
      "Brak dowodów treściowych w WILQ. WILQ potrzebuje danych z GSC, GA4, Ahrefs i WordPress przed planem treści.",
    safetyTitle: "Brama bezpieczeństwa treści",
    safetyText:
      "Plany treści, przepisywanie treści i szkice wymagają źródeł, dowodów i zgodności z realną ofertą. WILQ nie generuje obietnic bez pokrycia w danych.",
    connectorIds: [
      "google_search_console",
      "google_analytics_4",
      "ahrefs",
      "wordpress_ekologus",
      "wordpress_sklep",
      "google_merchant_center"
    ],
    textNeedles: ["content", "treści", "wordpress", "gsc", "ahrefs", "merchant"]
  },
  "/merchant": {
    title: "Merchant Center",
    description:
      "Widok feedu i produktów oparty o WILQ. Nie pokazuje rekomendacji, jeżeli brakuje dowodów z Merchant Center albo sprawdzonej akcji.",
    focusTitle: "Feed i produkty do sprawdzenia",
    emptyMessage:
      "Brak dowodów Merchant w WILQ. Uruchom odczyt Merchant Center, zanim WILQ zaproponuje zmiany feedu albo produktu.",
    safetyTitle: "Brama bezpieczeństwa feedu",
    safetyText:
      "Zmiana feedu wymaga podglądu akcji, sprawdzenia w WILQ i audytu. Ten ekran działa bez zapisu zmian, dopóki WILQ nie przygotuje poprawnej akcji do sprawdzenia.",
    connectorIds: ["google_merchant_center", "merchant_center"],
    textNeedles: []
  }
};

function MarketingBriefCard({ item }: { item: MarketingBriefItem }) {
  return (
    <article className="rounded-md border border-line p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{item.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {item.kind} / {item.priority_label}
          </p>
        </div>
        <StatusBadge value={item.risk} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{item.summary}</p>
      <p className="mt-3 text-sm font-medium text-ink">{item.next_step}</p>
      {item.blocker_reason ? (
        <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-2 text-xs text-wait">
          Blokada: {item.blocker_reason}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine
          label="Dowody"
          values={item.evidence_summary_label ? [item.evidence_summary_label] : []}
          empty="brak etykiety dowodów z WILQ"
        />
        <TraceLine
          label="Źródła"
          values={item.source_connector_labels}
          empty="źródła danych WILQ"
        />
        <TraceLine
          label="Akcje"
          values={item.action_summary_label ? [item.action_summary_label] : []}
          empty="brak akcji do sprawdzenia"
        />
      </div>
      {item.metric_facts.length > 0 ? <MetricFactChips facts={item.metric_facts.slice(0, 4)} /> : null}
    </article>
  );
}

export function BriefWorkflowSurface({ config }: { config: BriefSurfaceConfig }) {
  const marketingBrief = useQuery({
    queryKey: ["marketing-brief"],
    queryFn: getMarketingBrief
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });
  const tacticalQueue = useQuery({
    queryKey: ["tactical-queue"],
    queryFn: getTacticalQueue
  });

  if (marketingBrief.isLoading || actions.isLoading || tacticalQueue.isLoading) return <LoadingBand />;
  if (marketingBrief.error || !marketingBrief.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message={`Nie udało się odczytać briefu. ${config.title} nie może pokazać rekomendacji bez WILQ.`} />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message={`Nie udało się pobrać akcji do sprawdzenia. ${config.title} nie może pokazać podglądu zmian ani sprawdzenia w WILQ.`} />
      </main>
    );
  }

  const brief = marketingBrief.data;
  const allItems = brief.sections.flatMap((section) => section.items);
  const routeItems = allItems
    .filter((item) => itemMatchesBriefSurface(item, config))
    .sort((left, right) => right.priority - left.priority);
  const recommendations = routeItems.filter((item) => item.kind === "recommendation");
  const blockers = routeItems.filter((item) => item.kind === "blocker");
  const metricFacts = brief.top_metric_facts.filter((fact) =>
    config.connectorIds.includes(fact.source_connector)
  );
  const routeActionIds = uniqueValues(routeItems.flatMap((item) => item.action_ids));
  const routeActions = actions.data.filter((action) => routeActionIds.includes(action.id));

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{config.title}</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">{config.description}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Rekomendacje" value={recommendations.length} />
          <MetricTile label="Blokady" value={blockers.length} />
          <MetricTile label="Fakty" value={metricFacts.length} />
        </div>
      </div>

      <div className="grid gap-6">
        {routeItems.length === 0 ? (
          <BlockerNotice message={config.emptyMessage} />
        ) : (
          <section>
            <SectionHeading title={config.focusTitle} />
            <div className="grid gap-3 xl:grid-cols-2">
              {routeItems.map((item) => (
                <MarketingBriefCard key={item.id} item={item} />
              ))}
            </div>
          </section>
        )}

        {routeActionIds.length > 0 ? <ActionObjectFocus actions={routeActions} /> : null}

        {config.showTacticalQueue === false ? null : (
          <TacticalQueuePanel
            queue={tacticalQueue.data}
            connectorIds={config.connectorIds}
            limit={6}
            compact
            title="Taktyki z WILQ"
            isLoading={tacticalQueue.isLoading}
            isError={Boolean(tacticalQueue.error)}
          />
        )}

        <section className="rounded-md border border-line bg-white p-4">
          <div className="mb-3 flex items-start gap-3">
            <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
              <ShieldAlert aria-hidden="true" size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
                {config.safetyTitle}
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">{config.safetyText}</p>
            </div>
          </div>
          <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <TraceLine
              label="Dowody"
              values={uniqueValues(
                routeItems
                  .map((item) => item.evidence_summary_label)
                  .filter((label) => label.length > 0)
              )}
              empty="brak etykiety dowodów z WILQ"
            />
            <TraceLine
              label="Źródła"
              values={uniqueValues(routeItems.flatMap((item) => item.source_connector_labels))}
              empty="źródła danych WILQ"
            />
            <TraceLine
              label="Akcje"
              values={uniqueValues(
                routeItems
                  .map((item) => item.action_summary_label)
                  .filter((label) => label.length > 0)
              )}
              empty="brak akcji do sprawdzenia"
            />
          </div>
          {metricFacts.length > 0 ? <MetricFactChips facts={metricFacts.slice(0, 6)} /> : null}
        </section>
      </div>
    </main>
  );
}

function itemMatchesBriefSurface(item: MarketingBriefItem, config: BriefSurfaceConfig) {
  const searchable = `${item.id} ${item.title} ${item.summary} ${item.next_step}`.toLowerCase();
  return (
    item.source_connectors.some((connector) => config.connectorIds.includes(connector)) ||
    config.textNeedles.some((needle) => searchable.includes(needle))
  );
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}

function SectionHeading({ title }: { title: string }) {
  return <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-slate-600">{title}</h2>;
}
