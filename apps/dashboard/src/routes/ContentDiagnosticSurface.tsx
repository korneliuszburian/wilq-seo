import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import {
  ActionObject,
  ContentDiagnosticsResponse,
  ContentPreflightResponse,
  getActions,
  getContentDiagnostics,
  getContentPreflight,
} from "../lib/api";
import { ActionPreviewCard } from "../components/ActionPreviewCard";
import { formatContentMetricValue } from "../lib/contentLabels";
import {
  BlockerNotice,
  LabelChipRow,
  LoadingBand,
  MetricTile,
  PlainChipRow
} from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import {
  ActionFocus,
  ActionIdFocus,
} from "./ActionPanels";
import { shortPath } from "./TacticalQueuePanel";

type ContentDecisionItem = ContentDiagnosticsResponse["decision_queue"][number];
type ContentMetricFact = ContentDiagnosticsResponse["sections"][number]["metric_facts"][number];
type ContentPreflightItem = ContentPreflightResponse["items"][number];

export function ContentDiagnosticSurface({ title }: { title: string }) {
  const diagnostics = useQuery({
    queryKey: ["content-diagnostics"],
    queryFn: getContentDiagnostics
  });
  const preflight = useQuery({
    queryKey: ["content-preflight"],
    queryFn: getContentPreflight
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions,
    enabled: diagnostics.isSuccess
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać danych treści. Widok Content nie może udawać wniosków SEO bez danych źródłowych." />
      </main>
    );
  }

  const data = diagnostics.data;
  const routeActions = (actions.data ?? []).filter((action) => data.action_ids.includes(action.id));
  const operatorMetricTiles = contentOperatorMetricTiles(data);
  const latestStatuses = data.latest_refreshes.map((refresh) => {
    return `${refresh.connector_label}: ${refresh.status_label}`;
  });

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok SEO i treści z danych WILQ. Łączy zapytania i adresy z GSC,
            spis treści WordPress i akcje do sprawdzenia, żeby marketer wiedział co odświeżyć,
            scalić, utworzyć albo zablokować bez duplikowania treści.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          {operatorMetricTiles.slice(0, 3).map(([label, value]) => (
            <MetricTile key={label} label={label} value={value} />
          ))}
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Stan danych treści
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <PlainChipRow
            values={[
              data.live_data_status_label || "stan danych treści do sprawdzenia",
              ...data.connectors.map((connector) => `${connector.label}: ${connector.status_label}`)
            ]}
          />
        </div>
        <TraceLine label="Ostatnie odczyty" values={latestStatuses} />
      </section>

      <ContentPreflightPanel data={preflight.data} isLoading={preflight.isLoading} isError={Boolean(preflight.error)} />

      <ContentSelectedDecisionPanel data={data} />

      <ContentExpandableBriefPanel actions={routeActions} />

      <ContentExpandableReviewPanel data={data} />

      <ContentExpandableActionsPanel
        actions={routeActions}
        actionIds={data.action_ids}
        actionSummaryLabel={data.action_summary_label}
        isLoading={actions.isLoading}
        isError={Boolean(actions.error)}
      />
    </main>
  );
}

function ContentExpandableBriefPanel({ actions }: { actions: ActionObject[] }) {
  const [showBriefs, setShowBriefs] = useState(false);
  const briefCount = contentActionPreviewCardsFromActions(actions, "content_brief_review").length;
  const draftCount = contentActionPreviewCardsFromActions(
    actions,
    "wordpress_draft_payload_review"
  ).length;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Plany treści do sprawdzenia
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Pierwszy ekran pokazuje jeden wybrany kierunek treści. Rozwiń plany treści,
            gdy chcesz zobaczyć H1, H2, FAQ, CTA, blokady publikacji i szkice
            WordPress do sprawdzenia.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs">
          <MetricTile label="Plany treści" value={briefCount} />
          <MetricTile label="Szkice" value={draftCount} />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowBriefs((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showBriefs ? "Ukryj plany treści" : "Pokaż plany treści"}
      </button>

      {showBriefs ? <div className="mt-4"><ContentBriefPreviewPanel actions={actions} /></div> : null}
    </section>
  );
}

function ContentExpandableReviewPanel({ data }: { data: ContentDiagnosticsResponse }) {
  const [showReview, setShowReview] = useState(false);
  const operatorMetricTiles = contentOperatorMetricTiles(data);

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Pełny przegląd treści
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Rozwiń pełny przegląd, gdy chcesz zobaczyć kolejkę decyzji, status
            WordPress, GSC i Ahrefs, dowody w WILQ i bramę bezpieczeństwa treści.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          {operatorMetricTiles.slice(1, 4).map(([label, value]) => (
            <MetricTile key={label} label={label} value={value} />
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowReview((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showReview ? "Ukryj pełny przegląd treści" : "Pokaż pełny przegląd treści"}
      </button>

      {showReview ? (
        <div className="mt-4 grid gap-6">
          <ContentOperatorSummary data={data} />
          <ContentDiagnosticProof data={data} />
          <ContentSafetyGatePanel data={data} />
        </div>
      ) : null}
    </section>
  );
}

function ContentExpandableActionsPanel({
  actions,
  actionIds,
  actionSummaryLabel,
  isLoading,
  isError
}: {
  actions: ActionObject[];
  actionIds: string[];
  actionSummaryLabel: string;
  isLoading: boolean;
  isError: boolean;
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
            WILQ pokazuje dla Treści: {actionSummaryLabel}.
            Otwórz tę sekcję dopiero wtedy, gdy chcesz zapisać decyzję człowieka,
            wygenerować podgląd zmian albo sprawdzić warunki bezpiecznego zapisu.
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
          {isLoading ? (
            <ActionIdFocus
              actionIds={actionIds}
              actionSummaryLabel={actionSummaryLabel}
              note="Ładuję szczegóły akcji; decyzje contentowe powyżej są już oparte o dane WILQ."
            />
          ) : isError ? (
            <ActionIdFocus
              actionIds={actionIds}
              actionSummaryLabel={actionSummaryLabel}
              note="Nie udało się odczytać pełnych akcji. Linki do sprawdzenia zostają widoczne, ale podgląd zmian wymaga danych akcji."
            />
          ) : (
            <ActionFocus actions={actions} />
          )}
        </div>
      ) : null}
    </section>
  );
}

function ContentPreflightPanel({
  data,
  isLoading,
  isError
}: {
  data: ContentPreflightResponse | undefined;
  isLoading: boolean;
  isError: boolean;
}) {
  const item = data?.primary_item;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Czy można pisać?
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ najpierw sprawdza, czy bezpieczny kierunek to zachowanie,
            odświeżenie, scalenie, utworzenie czy blokada. Szkic i WordPress
            pozostają zablokowane, dopóki nie przejdą plan treści, ryzykowne
            obietnice i decyzja człowieka.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          <MetricTile label="Tryb" value={item ? item.recommended_mode_label : "brak"} />
          <MetricTile label="Status" value={item ? item.status_label : "brak"} />
          <MetricTile label="Blokady" value={data?.blocker_count ?? 0} />
          <MetricTile label="Plan treści" value={item?.sales_brief_allowed ? "możliwy" : "zablokowany"} />
        </div>
      </div>

      {isLoading ? (
        <p className="mt-3 text-sm text-slate-600">WILQ sprawdza bramkę pisania.</p>
      ) : isError || !data || !item ? (
        <BlockerNotice message="Nie udało się odczytać bramki pisania. Nie zaczynaj szkicu bez wyniku sprawdzenia." />
      ) : (
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          <div className="rounded-md border border-line bg-slate-50 p-3">
            <h3 className="text-sm font-semibold text-ink">Rekomendowany kierunek</h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {contentPreflightModeSentence(item)}
            </p>
            <TraceLine
              label="Adres"
              values={[
                item.final_canonical_url ?? item.intended_final_url ?? item.source_public_url ?? ""
              ].filter(Boolean).map(shortPath)}
              empty="do potwierdzenia"
            />
          </div>
          <div className="rounded-md border border-line bg-slate-50 p-3">
            <h3 className="text-sm font-semibold text-ink">Następny bezpieczny krok</h3>
            <p className="mt-2 text-sm font-medium leading-6 text-ink">{item.next_step}</p>
            <TraceLine label="Wspólne zapytania" values={[item.query_overlap_summary]} />
          </div>
          <div className="rounded-md border border-line bg-white p-3">
            <h3 className="text-sm font-semibold text-ink">Co blokuje szkic</h3>
            <TraceLine
              label="Brakuje"
              values={item.missing_inputs.slice(0, 5)}
              empty="brak dodatkowych braków w tej bramce"
            />
            <TraceLine
              label="Zakazy"
              values={item.blocked_claims.slice(0, 5)}
              empty="brak dodatkowych zakazów w tej bramce"
            />
          </div>
          <div className="rounded-md border border-line bg-white p-3">
            <h3 className="text-sm font-semibold text-ink">Dowody i istniejące treści</h3>
            <TraceLine
              label="Podobne URL-e"
              values={item.similar_existing_urls.slice(0, 4).map(shortPath)}
              empty="brak potwierdzonych podobnych URL-i"
            />
            <TraceLine
              label="Dowody"
              values={[item.evidence_summary_label]}
            />
          </div>
        </div>
      )}
    </section>
  );
}

function ContentSafetyGatePanel({ data }: { data: ContentDiagnosticsResponse }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa treści
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              WILQ może przygotować plan treści, kolejkę odświeżenia i podgląd zmian,
              ale nie publikuje ani nie zmienia WordPress bez sprawdzenia w WILQ,
              jawnej zgody operatora i audytu.
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

function ContentBriefPreviewPanel({ actions }: { actions: ActionObject[] }) {
  const previews = contentActionPreviewCardsFromActions(actions, "content_brief_review").slice(0, 4);
  const draftPreviews = contentActionPreviewCardsFromActions(
    actions,
    "wordpress_draft_payload_review"
  ).slice(0, 4);
  if (previews.length === 0 && draftPreviews.length === 0) return null;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Plany treści do sprawdzenia
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            Co WILQ może przygotować bez publikacji
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            To są propozycje do sprawdzenia w WILQ. Każda wymaga kontroli
            GSC i WordPress, duplikatów i decyzji operatora przed jakąkolwiek
            zmianą treści.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs">
          <MetricTile label="Podglądy" value={previews.length} />
          <MetricTile
            label="Zapis zmian"
            value="zablokowane"
          />
        </div>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {previews.map(({ actionId, card }) => (
          <div key={`${actionId}-${card.id}`} className="grid gap-2">
            <ActionPreviewCard card={card} />
            <a className="text-xs font-medium text-ink underline" href={`/actions/${actionId}`}>
              Otwórz akcję do sprawdzenia
            </a>
          </div>
        ))}
      </div>
      {draftPreviews.length > 0 ? (
        <div className="mt-5 rounded-md border border-line bg-white p-3">
          <div className="mb-3">
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
              Szkic WordPress po sprawdzeniu
            </div>
            <h3 className="mt-1 text-sm font-semibold text-ink">
              Co WILQ może przygotować jako szkic WordPress
            </h3>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              Te szkice pojawiają się dopiero po zapisanym sprawdzeniu propozycji.
              Status pozostaje jako szkic, a zmiany i publikacja są zablokowane.
            </p>
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            {draftPreviews.map(({ actionId, card }) => (
              <div key={`${actionId}-${card.id}`} className="grid gap-2">
                <ActionPreviewCard card={card} />
                <a className="text-xs font-medium text-ink underline" href={`/actions/${actionId}`}>
                  Otwórz akcję do sprawdzenia
                </a>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function ContentSelectedDecisionPanel({
  data
}: {
  data: ContentDiagnosticsResponse;
}) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const topDecisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is ContentDecisionItem => Boolean(decision));
  const primaryDecision =
    (data.marketer_decision?.technical_decision_id
      ? decisionsById.get(data.marketer_decision.technical_decision_id)
      : undefined) ??
    topDecisions[0] ??
    data.decision_queue[0];
  const blockedClaims = uniqueValues([
    ...(primaryDecision?.blocked_claims ?? [])
  ]);
  const missingInputs = uniqueValues([
    ...(primaryDecision?.inventory_gate_status_label ? [primaryDecision.inventory_gate_status_label] : []),
    ...(primaryDecision?.canonical_gate_status_label ? [primaryDecision.canonical_gate_status_label] : []),
    ...(primaryDecision?.duplicate_gate_status_label ? [primaryDecision.duplicate_gate_status_label] : [])
  ]);
  const sourceConnectorLabels = uniqueValues([
    ...(primaryDecision?.source_connector_labels ?? [])
  ]);
  const marketerDecision = data.marketer_decision;
  const panelBlockedClaims = marketerDecision?.blocked_claims ?? blockedClaims;
  const panelMissingInputs = marketerDecision?.missing_inputs ?? missingInputs;
  const panelEvidenceSummary =
    marketerDecision?.evidence_summary ??
    primaryDecision?.evidence_summary_label ??
    "brak dowodów źródłowych";
  const panelSourceConnectors =
    marketerDecision?.source_connector_labels?.length
      ? marketerDecision.source_connector_labels
      : sourceConnectorLabels;
  const panelMeasurementPlan =
    marketerDecision?.measurement_plan ?? contentSelectedMeasurementPlan();

  if (!primaryDecision) {
    return (
      <section className="mb-6 rounded-md border border-action/30 bg-action/5 p-4">
        <h2 className="text-base font-semibold tracking-normal text-ink">
          Dzisiejszy plan treści do sprawdzenia
        </h2>
        <BlockerNotice message="Brak decyzji contentowych. Najpierw odśwież dane GSC, WordPress i Ahrefs w WILQ." />
      </section>
    );
  }

  return (
    <section className="mb-6 rounded-md border border-action/30 bg-action/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-action">
            {marketerDecision?.mode_label ?? "Dzisiejszy plan treści do sprawdzenia"}
          </div>
          <h2 className="mt-1 text-lg font-semibold tracking-normal text-ink">
            {marketerDecision?.decision ??
              primaryDecision.title ??
              "Wybrany temat do zachowania albo odświeżenia"}
          </h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
            {marketerDecision?.content_angle ?? primaryDecision.summary ?? primaryDecision.rationale}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          {contentSelectedMetricTiles(primaryDecision, marketerDecision?.metric_tiles).map(([label, value]) => (
            <MetricTile key={label} label={label} value={value} />
          ))}
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Dlaczego to ma znaczenie</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {marketerDecision?.why_it_matters ?? primaryDecision.rationale}
          </p>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny następny krok</h3>
          <p className="mt-2 text-sm font-medium leading-6 text-ink">
            {marketerDecision?.safe_next_action ?? primaryDecision.next_step}
          </p>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Kierunek treści</h3>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine
              label="H1"
              values={marketerDecision?.h1_direction ? [marketerDecision.h1_direction] : []}
              empty="do doprecyzowania w planie treści"
            />
            <TraceLine
              label="H2"
              values={marketerDecision?.h2_direction?.slice(0, 3) ?? []}
              empty="do doprecyzowania w planie treści"
            />
            <TraceLine
              label="FAQ"
              values={marketerDecision?.faq_direction?.slice(0, 3) ?? []}
              empty="do doprecyzowania w planie treści"
            />
            <TraceLine
              label="Wezwanie do działania"
              values={marketerDecision?.cta_direction ? [marketerDecision.cta_direction] : []}
              empty="do doprecyzowania w planie treści"
            />
          </div>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Adresy i podgląd</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            ekologus.pl i sklep.ekologus.pl są źródłem prawdy. Adres podglądu jest
            opcjonalny i nie jest docelowym adresem SEO.
          </p>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine
              label="Źródło"
              values={[
                marketerDecision?.source_public_url ??
                  primaryDecision.page ??
                  ""
              ]
                .filter(Boolean)
                .map(shortPath)}
              empty="adres źródłowy do potwierdzenia"
            />
            <TraceLine
              label="Podgląd"
              values={[
                marketerDecision?.preview_url ??
                  ""
              ].filter(Boolean).map(shortPath)}
              empty="brak podglądu"
            />
            <TraceLine
              label="Docelowo"
              values={[
                marketerDecision?.final_canonical_url ??
                  marketerDecision?.intended_final_url ??
                  ""
              ]
                .filter(Boolean)
                .map(shortPath)}
              empty="do potwierdzenia"
            />
          </div>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Dowody i źródła</h3>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine label="Dowody" values={[panelEvidenceSummary]} />
            <TraceLine label="Źródła" values={panelSourceConnectors} />
            <TraceLine
              label="Fakty"
              values={marketerDecision?.source_facts?.slice(0, 4) ?? []}
              empty="zobacz szczegóły niżej"
            />
          </div>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Czego WILQ nie zrobi teraz</h3>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine
              label="Blokady"
              values={panelBlockedClaims.slice(0, 6)}
            />
            <TraceLine label="Brakuje" values={panelMissingInputs.slice(0, 6)} />
          </div>
        </div>
      </div>

      <div className="mt-3 rounded-md border border-line bg-white p-3">
        <h3 className="text-sm font-semibold text-ink">Jak później sprawdzimy efekt</h3>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {panelMeasurementPlan}
        </p>
      </div>
    </section>
  );
}

function ContentOperatorSummary({ data }: { data: ContentDiagnosticsResponse }) {
  const summary = data.operator_summary;
  const operatorMetricTiles = contentOperatorMetricTiles(data);
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const topDecisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is ContentDecisionItem => Boolean(decision));
  const actionIds = summary.action_ids;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Przegląd treści
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            {summary.title}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {summary.summary}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          {operatorMetricTiles.map(([label, value]) => (
            <MetricTile key={label} label={label} value={value} />
          ))}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {topDecisions.length > 0 ? (
            topDecisions.map((decision) => (
              <ContentDecisionCard key={decision.id} decision={decision} />
            ))
          ) : (
            <BlockerNotice message="Brak decyzji contentowych. Najpierw uruchom odczyt GSC i WordPress." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb treści</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine
              label="Tryby decyzji"
              values={summary.decision_type_labels}
              empty="brak trybów decyzji"
            />
            <TraceLine
              label="Dopasowania WordPress"
              values={[
                `potwierdzone: ${summary.confirmed_wordpress_count}`,
                `brak potwierdzenia: ${summary.missing_wordpress_count}`
              ]}
            />
            <TraceLine
              label="Publiczne URL-e"
              values={[
                `potwierdzone URL-e: ${summary.current_site_match_count}`
              ]}
            />
            <TraceLine
              label="Dowody"
              values={[summary.evidence_summary_label]}
              empty="brak dowodów źródłowych"
            />
            <TraceLine label="Akcje" values={[summary.action_summary_label]} />
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

function contentOperatorMetricTiles(data: ContentDiagnosticsResponse) {
  return Object.entries(data.operator_summary.metric_tiles);
}

function ContentDecisionCard({
  decision
}: {
  decision: ContentDecisionItem;
}) {
  const canonicalUrl = decision.final_canonical_url ?? decision.intended_final_url;
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{contentDecisionTitle(decision)}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {decision.decision_type_label || "typ decyzji do sprawdzenia"}
          </p>
        </div>
        <StatusBadge value={decision.status} label={decision.status_label} />
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">
        {decision.summary ?? decision.rationale}
      </p>
      {decision.summary ? (
        <p className="mt-1 text-xs leading-5 text-slate-500">{decision.rationale}</p>
      ) : null}
      <p className="mt-2 text-sm font-medium text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
        {decision.page ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Strona: {shortPath(decision.page)}
          </span>
        ) : null}
        {decision.queries.length > 0 ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Zapytania: {decision.queries.slice(0, 4).join(", ")}
          </span>
        ) : null}
        {decision.wordpress_match ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            WordPress: {decision.wordpress_match_label || "stan spisu do sprawdzenia"}
          </span>
        ) : null}
        {decision.wordpress_match_confidence ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Dopasowanie: {decision.wordpress_match_confidence_label || "pewność dopasowania do sprawdzenia"}
          </span>
        ) : null}
        {canonicalUrl ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Kanoniczny: {shortPath(canonicalUrl)}
          </span>
        ) : null}
        {decision.preview_url ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Podgląd: {shortPath(decision.preview_url)}
          </span>
        ) : null}
        {decision.inventory_gate_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Spis: {decision.inventory_gate_status_label || "status spisu do sprawdzenia"}
          </span>
        ) : null}
        {decision.canonical_gate_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Kanoniczny: {decision.canonical_gate_status_label || "status URL kanonicznego do sprawdzenia"}
          </span>
        ) : null}
        {decision.duplicate_gate_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Duplikaty: {decision.duplicate_gate_status_label || "status duplikatów do sprawdzenia"}
          </span>
        ) : null}
      </div>
      {decision.content_gate_summary ? (
        <p className="mt-2 rounded border border-line bg-white px-3 py-2 text-xs text-slate-700">
          {decision.content_gate_summary}
        </p>
      ) : null}
      {decision.ahrefs_candidate_rows.length > 0 ? (
        <div className="mt-3 rounded-md border border-line bg-white p-3">
          <h4 className="text-sm font-semibold text-ink">Ahrefs: akcje do sprawdzenia</h4>
          <div className="mt-2 grid gap-2">
            {decision.ahrefs_candidate_rows.slice(0, 3).map((candidate) => (
              <div key={candidate.id} className="rounded border border-line bg-slate-50 p-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-ink">{candidate.topic}</div>
                    <LabelChipRow
                      className="mt-1 gap-1"
                      chips={[
                        { label: "Typ", value: candidate.gap_type_label || "typ luki do sprawdzenia" },
                        { label: "Trafność", value: candidate.relevance_status_label || "trafność do sprawdzenia" },
                        { label: "Ocena WILQ", value: candidate.relevance_score }
                      ]}
                    />
                  </div>
                  <div className="flex flex-wrap gap-1 text-xs">
                    <span className="rounded border border-line bg-white px-2 py-1">
                      GSC: {candidate.gsc_demand_label || "popyt GSC do sprawdzenia"}
                    </span>
                    <span className="rounded border border-line bg-white px-2 py-1">
                      WP: {candidate.wordpress_inventory_match_label || "spis WordPress do sprawdzenia"}
                    </span>
                  </div>
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-600">{candidate.next_step}</p>
                <TraceLine
                  label="Powody"
                  values={candidate.business_relevance_reason_labels}
                />
                <TraceLine
                  label="Wspólne zapytania GSC"
                  values={candidate.gsc_overlap_terms.slice(0, 3)}
                  empty="brak wspólnych zapytań w GSC"
                />
                <TraceLine
                  label="Powiązane URL-e WordPress"
                  values={candidate.wordpress_overlap_urls.map(shortPath).slice(0, 3)}
                  empty="brak powiązanych URL-i WordPress"
                />
              </div>
            ))}
          </div>
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Dowody"
          values={[decision.evidence_summary_label]}
          empty="brak dowodów źródłowych"
        />
        <TraceLine label="Źródła" values={decision.source_connector_labels} />
        <TraceLine label="Akcje" values={[decision.action_summary_label]} />
        <TraceLine label="Nie wolno twierdzić" values={decision.blocked_claim_labels} />
      </div>
      {decision.metric_facts.length > 0 ? (
        <ContentMetricTiles facts={decision.metric_facts.slice(0, 4)} />
      ) : null}
    </article>
  );
}

function ContentDiagnosticProof({ data }: { data: ContentDiagnosticsResponse }) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  const visibleMetricFacts = metricFacts.slice(0, 4);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i warunki decyzji treści
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót danych i ograniczeń WILQ. Decyzje dla marketera są powyżej;
            tutaj widać, z jakich źródeł i blokad wynikają.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Sekcje danych" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Dowody" value={data.evidence_summary_label} />
        </div>
      </div>
      {visibleMetricFacts.length > 0 ? <ContentMetricTiles facts={visibleMetricFacts} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={data.sections.map((section) => section.title)} />
        <TraceLine label="Źródła danych" values={data.source_connector_labels} />
        <TraceLine label="Akcje" values={[data.action_summary_label]} />
        <TraceLine
          label="Nie wolno twierdzić"
          values={data.sections.flatMap((section) => section.blocked_claim_labels)}
        />
      </div>
    </section>
  );
}

function ContentMetricTiles({ facts }: { facts: ContentMetricFact[] }) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
      {facts.map((fact, index) => (
        <MetricTile
          key={`${fact.source_connector}-${fact.name}-${fact.evidence_id}-${index}`}
          label={fact.metric_label}
          value={formatContentMetricValue(fact.name, fact.value)}
        />
      ))}
    </div>
  );
}

function contentPreflightModeSentence(item: ContentPreflightItem) {
  if (item.recommended_mode === "preserve") {
    return "Najbezpieczniej zachować istniejącą treść. Nie ma jeszcze powodu, żeby ją przepisywać.";
  }
  if (item.recommended_mode === "refresh") {
    return "WILQ wskazuje odświeżenie istniejącej treści. Nowy artykuł pozostaje zablokowany.";
  }
  if (item.recommended_mode === "merge") {
    return "WILQ wskazuje scalenie albo decyzję o połączeniu tematów przed pisaniem.";
  }
  if (item.recommended_mode === "create") {
    return "WILQ dopuszcza nową treść, ale szkic nadal wymaga planu treści, sprawdzenia ryzykownych obietnic i decyzji człowieka.";
  }
  return "WILQ blokuje pisanie. Najpierw trzeba uzupełnić brakujące dane albo rozwiązać ryzyko.";
}

function contentDecisionTitle(decision: ContentDecisionItem) {
  return decision.title;
}

function contentActionPreviewCardsFromActions(actions: ActionObject[], kind: string) {
  return actions.flatMap((action) =>
    action.preview_cards
      .filter((card) => card.kind === kind)
      .map((card) => ({ actionId: action.id, card }))
  );
}

function contentSelectedMetricTiles(
  decision: ContentDecisionItem,
  marketerMetricTiles: Record<string, string | number> | undefined
): Array<[string, string | number]> {
  const marketerRows = Object.entries(marketerMetricTiles ?? {}).slice(0, 4);
  if (marketerRows.length) return marketerRows;
  return Object.entries(decision.metric_tiles)
    .slice(0, 4)
    .map(([label, value]): [string, string | number] => [label, value]);
}

function contentSelectedMeasurementPlan() {
  return "Najpierw zapisz sprawdzenie planu treści. Bez publikacji oraz danych po publikacji WILQ nie ocenia sukcesu ani porażki.";
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
