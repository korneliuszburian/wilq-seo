import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck, RefreshCw, ShieldAlert } from "lucide-react";

import {
  ActionObject,
  ActionReviewRequest,
  ContentDiagnosticsResponse,
  ContentPreflightResponse,
  ConnectorStatus,
  getActions,
  getContentDiagnostics,
  getContentPreflight,
  reviewAction
} from "../lib/api";
import { connectorLabelsFromStatuses } from "../lib/connectorLabels";
import { formatContentMetricValue } from "../lib/contentLabels";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import {
  ActionObjectFocus,
  ActionObjectIdFocus,
} from "./ActionObjectPanels";
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
  const ahrefsWordPressOverlapCount = contentAhrefsWordPressOverlapCount(data);
  const latestStatuses = data.latest_refreshes.map((refresh) => {
    const [label] = connectorLabelsFromStatuses([refresh.connector_id], data.connectors);
    return `${label}: ${refresh.status_label}`;
  });

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok SEO i treści z danych WILQ. Łączy zapytania i URL-e z GSC,
            spis treści WordPress i akcje do sprawdzenia, żeby marketer wiedział co odświeżyć,
            scalić, utworzyć albo zablokować bez duplikowania treści.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Zapytania/URL" value={data.query_page_count} />
          <MetricTile label="GSC↔WP" value={data.matched_inventory_count} />
          <MetricTile label="Ahrefs↔WP" value={ahrefsWordPressOverlapCount} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status SEO / Content
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "metryki treści dostępne" : "brak metryk treści"}
              <span className="sr-only">; </span>
            </span>
            {data.connectors.map((connector) => (
              <span
                key={connector.id}
                className="rounded-md border border-line px-2 py-1 text-slate-600"
              >
                {connector.label}: {connector.status_label}
                <span className="sr-only">; </span>
              </span>
            ))}
          </div>
        </div>
        <TraceLine label="Ostatnie odczyty" values={latestStatuses} />
      </section>

      <ContentPreflightPanel data={preflight.data} isLoading={preflight.isLoading} isError={Boolean(preflight.error)} />

      <ContentSelectedDecisionPanel data={data} actions={routeActions} />

      <ContentExpandableBriefPanel actions={routeActions} />

      <ContentExpandableReviewPanel data={data} />

      <ContentExpandableActionsPanel
        actions={routeActions}
        actionIds={data.action_ids}
        isLoading={actions.isLoading}
        isError={Boolean(actions.error)}
      />
    </main>
  );
}

function ContentExpandableBriefPanel({ actions }: { actions: ActionObject[] }) {
  const [showBriefs, setShowBriefs] = useState(false);
  const briefCount = contentBriefPreviewItemsFromActions(actions).length;
  const draftCount = wordpressDraftPayloadPreviewItemsFromActions(actions).length;

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
  const ahrefsWordPressOverlapCount = contentAhrefsWordPressOverlapCount(data);

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Pełny przegląd Content
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Rozwiń pełny przegląd, gdy chcesz zobaczyć kolejkę decyzji, status
            WordPress/GSC/Ahrefs, dowody techniczne i bramę bezpieczeństwa treści.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
          <MetricTile label="GSC↔WP" value={data.matched_inventory_count} />
          <MetricTile label="Ahrefs↔WP" value={ahrefsWordPressOverlapCount} />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowReview((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showReview ? "Ukryj pełny przegląd Content" : "Pokaż pełny przegląd Content"}
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
  isLoading,
  isError
}: {
  actions: ActionObject[];
  actionIds: string[];
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
            WILQ ma {formatContentActionCount(actionIds.length)} dla Content.
            Otwórz je dopiero wtedy, gdy chcesz zapisać decyzję człowieka,
            wygenerować podgląd zmian albo sprawdzić warunki bezpiecznego zapisu.
          </p>
        </div>
        <MetricTile label="Akcje" value={formatContentActionCount(actionIds.length)} />
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
            <ActionObjectIdFocus
              actionIds={actionIds}
              note="Ładuję szczegóły akcji; decyzje contentowe powyżej są już oparte o dane WILQ."
            />
          ) : isError ? (
            <ActionObjectIdFocus
              actionIds={actionIds}
              note="Nie udało się odczytać pełnych akcji. Linki do sprawdzenia zostają widoczne, ale podgląd zmian wymaga danych akcji."
            />
          ) : (
            <ActionObjectFocus actions={actions} />
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
              values={[formatContentEvidenceCount(item.evidence_ids.length)]}
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

type ContentBriefPreviewItem = {
  action_id: string;
  candidate_id: string;
  source_type: string;
  source_type_label: string;
  mode: string;
  mode_label: string;
  topic: string;
  source_public_url?: string | null;
  preview_url?: string | null;
  intended_final_url?: string | null;
  final_canonical_url?: string | null;
  inventory_gate_status?: string | null;
  canonical_gate_status?: string | null;
  duplicate_gate_status?: string | null;
  content_gate_summary?: string | null;
  competitor_domain?: string | null;
  wordpress_inventory_match?: string | null;
  gsc_demand?: string | null;
  metric_snapshot: Record<string, string | number | boolean | null>;
  metric_snapshot_labels?: Record<string, string>;
  brief_goal: string;
  intent?: string | null;
  content_angle?: string | null;
  audience?: string | null;
  key_objections?: string[];
  h1_direction?: string | null;
  seo_title_direction?: string | null;
  meta_description_direction?: string | null;
  h2_direction?: string[];
  faq_direction?: string[];
  schema_direction?: string | null;
  cta_direction?: string | null;
  internal_link_direction?: string[];
  legal_review_notes?: string[];
  brand_voice_notes?: string[];
  publication_readiness_status?: string | null;
  publication_readiness_status_label: string;
  publication_blockers?: string[];
  publication_blocker_labels?: string[];
  source_facts?: string[];
  missing_evidence?: string[];
  forbidden_claims?: string[];
  required_validation: string[];
  required_validation_labels?: string[];
  blocked_claims: string[];
  blocked_claim_labels: string[];
  source_connectors?: string[];
  evidence_ids: string[];
  apply_allowed: boolean;
  api_mutation_ready: boolean;
};

function ContentBriefPreviewPanel({ actions }: { actions: ActionObject[] }) {
  const previews = contentBriefPreviewItemsFromActions(actions).slice(0, 4);
  const draftPreviews = wordpressDraftPayloadPreviewItemsFromActions(actions).slice(0, 4);
  if (previews.length === 0) return null;

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
            GSC/WordPress, duplikatów i decyzji operatora przed jakąkolwiek
            zmianą treści.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs">
          <MetricTile label="Podglądy" value={previews.length} />
          <MetricTile
            label="Zapis zmian"
            value={previews.some((preview) => preview.apply_allowed) ? "otwarte" : "zablokowane"}
          />
        </div>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {previews.map((preview) => (
          <ContentBriefPreviewCard
            key={`${preview.action_id}-${preview.candidate_id}`}
            preview={preview}
          />
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
            {draftPreviews.map((preview) => (
              <WordPressDraftPayloadPreviewCard
                key={`${preview.action_id}-${preview.candidate_id}`}
                preview={preview}
              />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function ContentBriefPreviewCard({ preview }: { preview: ContentBriefPreviewItem }) {
  const queryClient = useQueryClient();
  const reviewMutation = useMutation({
    mutationFn: () => reviewAction(preview.action_id, contentBriefReviewRequest(preview)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions"] });
      void queryClient.invalidateQueries({ queryKey: ["content-diagnostics"] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });

  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{preview.topic}</h3>
          <p className="mt-0.5 text-xs uppercase tracking-normal text-slate-500">
            {preview.source_type_label} / {preview.mode_label}
          </p>
        </div>
        <StatusBadge value={preview.apply_allowed ? "ready" : "blocked"} />
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{preview.brief_goal}</p>
      <div className="mt-3 grid gap-2 rounded-md border border-line bg-white p-3 text-xs leading-5 text-slate-600">
        {preview.intent ? <div>Intencja: {preview.intent}</div> : null}
        {preview.content_angle ? <div>Kąt treści: {preview.content_angle}</div> : null}
        {preview.audience ? <div>Odbiorca: {preview.audience}</div> : null}
        {preview.h1_direction ? <div>H1: {preview.h1_direction}</div> : null}
        {preview.seo_title_direction ? <div>Title: {preview.seo_title_direction}</div> : null}
        {preview.meta_description_direction ? (
          <div>Meta: {preview.meta_description_direction}</div>
        ) : null}
        {preview.cta_direction ? <div>CTA: {preview.cta_direction}</div> : null}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        {Object.entries(preview.metric_snapshot).slice(0, 4).map(([label, value]) => (
          <MetricTile
            key={`${preview.candidate_id}-${label}`}
            label={preview.metric_snapshot_labels?.[label] ?? label}
            value={contentBriefMetricValue(label, value)}
          />
        ))}
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Obiekcje" values={(preview.key_objections ?? []).slice(0, 3)} />
        <TraceLine label="H2" values={(preview.h2_direction ?? []).slice(0, 4)} />
        <TraceLine label="FAQ" values={(preview.faq_direction ?? []).slice(0, 4)} />
        <TraceLine label="Schema" values={preview.schema_direction ? [preview.schema_direction] : []} />
        <TraceLine
          label="Adresy"
          values={contentAddressValues(preview)}
          empty="brak"
        />
        <TraceLine
          label="Status publikacji"
          values={preview.publication_readiness_status_label ? [preview.publication_readiness_status_label] : []}
          empty="brak"
        />
        <TraceLine
          label="Blokady publikacji"
          values={(preview.publication_blocker_labels ?? []).slice(0, 6)}
          empty="brak"
        />
        <TraceLine
          label="Kontrola prawna"
          values={(preview.legal_review_notes ?? []).slice(0, 4)}
          empty="brak"
        />
        <TraceLine
          label="Ton marki"
          values={(preview.brand_voice_notes ?? []).slice(0, 4)}
          empty="brak"
        />
        <TraceLine label="Linkowanie" values={(preview.internal_link_direction ?? []).slice(0, 3)} />
        <TraceLine label="Źródła faktów" values={(preview.source_facts ?? []).slice(0, 4)} />
        <TraceLine label="Brakujące dowody" values={(preview.missing_evidence ?? []).slice(0, 3)} />
        <TraceLine
          label="Warunki sprawdzenia"
          values={(preview.required_validation_labels ?? []).slice(0, 4)}
        />
        <TraceLine
          label="Nie wolno obiecać"
          values={(preview.blocked_claim_labels ?? []).slice(0, 4)}
        />
        <TraceLine
          label="Dowody"
          values={[formatContentEvidenceCount(preview.evidence_ids.length)]}
          empty="brak"
        />
        <TraceLine label="Akcja" values={["1 akcja"]} />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => reviewMutation.mutate()}
          disabled={reviewMutation.isPending}
          className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {reviewMutation.isPending ? (
            <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
          ) : (
            <ClipboardCheck aria-hidden="true" size={15} />
          )}
          {reviewMutation.isPending ? "Zapisuję sprawdzenie" : "Zapisz sprawdzenie planu treści"}
        </button>
        <span className="text-xs text-slate-600">
          Zapisuje wybór planu treści do sprawdzenia. Nie publikuje i nie zapisuje zmian.
        </span>
      </div>
      {reviewMutation.data ? (
        <p className="mt-2 rounded-md border border-line bg-white p-2 text-xs leading-5 text-slate-600">
          Zapisano sprawdzenie: {reviewMutation.data.audit_event.event_type_label}. Zapis zmian nadal:{" "}
          {reviewMutation.data.review_gate.apply_allowed ? "otwarte" : "zablokowane"}.
        </p>
      ) : null}
      {reviewMutation.error instanceof Error ? (
        <p className="mt-2 text-xs leading-5 text-risk">
          Nie udało się zapisać sprawdzenia: {reviewMutation.error.message}
        </p>
      ) : null}
    </article>
  );
}

type WordPressDraftPayloadPreviewItem = {
  action_id: string;
  preview_contract: string;
  candidate_id: string;
  operation_type: string;
  post_status: string;
  topic: string;
  intent?: string | null;
  source_public_url?: string | null;
  preview_url?: string | null;
  intended_final_url?: string | null;
  final_canonical_url?: string | null;
  inventory_gate_status?: string | null;
  canonical_gate_status?: string | null;
  duplicate_gate_status?: string | null;
  content_gate_summary?: string | null;
  content_gate_status_summary?: string[];
  draft_generation_status?: string | null;
  draft_blockers?: string[];
  draft_blocker_labels?: string[];
  draft_generation_contract?: {
    contract_version?: string;
    language?: string;
    status?: string;
    allowed_output_kind?: string;
    blocked_until?: string[];
    requires_passed_gates?: string[];
    output_must_include?: string[];
    forbidden_outputs?: string[];
  };
  draft_generation_summary?: string[];
  draft_readiness_review_contract?: {
    contract_version?: string;
    scope?: string;
    allowed_outcomes?: string[];
    required_fields?: string[];
    blocked_outputs?: string[];
  };
  draft_readiness_review_contract_summary?: string[];
  draft_readiness_review_recorded_outcome?: string | null;
  canonical_review_recorded_outcome?: string | null;
  duplicate_review_recorded_outcome?: string | null;
  legal_factual_review_recorded_outcome?: string | null;
  human_review_recorded_outcome?: string | null;
  draft_readiness_review_notes?: string | null;
  draft_readiness_review_summary?: string[];
  wordpress_draft_handoff_status?: string | null;
  wordpress_draft_handoff_blockers?: string[];
  wordpress_draft_handoff_blocker_labels?: string[];
  wordpress_draft_handoff_summary?: string[];
  wordpress_draft_handoff_contract?: {
    contract_version?: string;
    scope?: string;
    final_canonical_url?: string | null;
    status?: string;
    blocked_until?: string[];
    requires_passed_gates?: string[];
    required_next_action_contract?: string;
    blocked_outputs?: string[];
  };
  wordpress_draft_handoff_contract_summary?: string[];
  post_publication_measurement_plan?: {
    contract_version?: string;
    scope?: string;
    final_canonical_url?: string | null;
    status?: string;
    baseline_window?: string;
    followup_windows?: string[];
    required_source_connectors?: string[];
    required_metric_groups?: string[];
    requires_before_claims?: string[];
    blocked_outputs?: string[];
  };
  post_publication_measurement_summary?: string[];
  draft_payload: {
    post_status?: string;
    post_status_label?: string;
    post_title?: string;
    post_excerpt_direction?: string;
    content_blocks?: Array<{ section: string; section_label?: string; instruction: string }>;
  };
  required_validation: string[];
  required_validation_labels?: string[];
  blocked_claims: string[];
  blocked_claim_labels: string[];
  operation_type_label: string;
  post_status_label: string;
  draft_generation_status_label?: string | null;
  evidence_ids: string[];
  mutation_allowed: boolean;
  apply_allowed: boolean;
  api_mutation_ready: boolean;
};

function WordPressDraftPayloadPreviewCard({
  preview
}: {
  preview: WordPressDraftPayloadPreviewItem;
}) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-ink">
            {preview.draft_payload.post_title ?? `Szkic: ${preview.topic}`}
          </h4>
          <p className="mt-0.5 text-xs uppercase tracking-normal text-slate-500">
            {preview.operation_type_label} / {preview.post_status_label}
          </p>
        </div>
        <StatusBadge value={preview.mutation_allowed ? "ready" : "blocked"} />
      </div>
      {preview.draft_generation_status ? (
        <p className="mt-2 rounded border border-line bg-white px-3 py-2 text-xs font-medium text-ink">
          Status szkicu: {preview.draft_generation_status_label ?? preview.draft_generation_status}
        </p>
      ) : null}
      <p className="mt-2 text-xs leading-5 text-slate-600">
        {preview.draft_payload.post_excerpt_direction ??
          "Szkic zmian do sprawdzenia. Nie publikuje i nie zapisuje zmian."}
      </p>
      {preview.intent ? (
        <p className="mt-2 text-xs text-slate-600">Intencja szkicu: {preview.intent}</p>
      ) : null}
      {preview.final_canonical_url ?? preview.intended_final_url ?? preview.source_public_url ? (
        <p className="mt-2 text-xs text-slate-600">
          URL:{" "}
          {shortPath(preview.final_canonical_url ?? preview.intended_final_url ?? preview.source_public_url ?? "")}
        </p>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Adresy"
          values={contentAddressValues(preview)}
          empty="brak"
        />
        <TraceLine label="Kontrole treści" values={contentDraftGateValues(preview)} empty="brak" />
        <TraceLine
          label="Co blokuje szkic"
          values={(preview.draft_blocker_labels ?? []).slice(0, 6)}
          empty="brak"
        />
        <TraceLine
          label="Warunki szkicu"
          values={contentDraftContractValues(preview)}
          empty="brak"
        />
        <TraceLine
          label="Gotowość do sprawdzenia"
          values={contentDraftReadinessReviewValues(preview)}
          empty="brak zapisu"
        />
        <TraceLine
          label="Kontrola szkicu"
          values={contentDraftReadinessContractValues(preview)}
          empty="brak"
        />
        <TraceLine
          label="Szkic WordPress"
          values={contentWordPressDraftHandoffValues(preview)}
          empty="brak"
        />
        <TraceLine
          label="Warunki szkicu WordPress"
          values={contentWordPressDraftHandoffContractValues(preview)}
          empty="brak"
        />
        <TraceLine
          label="Pomiar po publikacji"
          values={contentPostPublicationMeasurementValues(preview)}
          empty="brak"
        />
        <TraceLine
          label="Bloki"
          values={(preview.draft_payload.content_blocks ?? [])
            .slice(0, 4)
            .map((block) => block.section_label ?? block.section)}
        />
        <TraceLine
          label="Warunki sprawdzenia"
          values={(preview.required_validation_labels ?? []).slice(0, 4)}
        />
        <TraceLine
          label="Nie wolno obiecać"
          values={(preview.blocked_claim_labels ?? []).slice(0, 4)}
        />
        <TraceLine
          label="Dowody"
          values={[formatContentEvidenceCount(preview.evidence_ids.length)]}
          empty="brak"
        />
        <TraceLine label="Akcja" values={["1 akcja"]} />
      </div>
    </article>
  );
}

function contentBriefReviewRequest(preview: ContentBriefPreviewItem): ActionReviewRequest {
  return {
    outcome: "approved_for_prepare",
    reviewed_by: "operator_local_dashboard",
    notes: `Wybrano propozycję planu treści ${preview.candidate_id} (${preview.topic}) do dalszego przeglądu. Ten zapis nie publikuje treści i nie zapisuje zmian.`,
    checked_items: uniqueValues([
      `candidate:${preview.candidate_id}`,
      `source_type:${preview.source_type}`,
      `mode:${preview.mode}`,
      ...preview.required_validation.slice(0, 5)
    ]),
    blockers: uniqueValues([
      "payload_apply_allowed_false",
      "wordpress_write_not_requested",
      ...preview.blocked_claims.slice(0, 5).map((claim) => `blocked_claim:${claim}`)
    ])
  };
}

function ContentSelectedDecisionPanel({
  data,
  actions
}: {
  data: ContentDiagnosticsResponse;
  actions: ActionObject[];
}) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const previews = contentBriefPreviewItemsFromActions(actions);
  const topDecisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is ContentDecisionItem => Boolean(decision));
  const primaryDecision =
    topDecisions.find((decision) =>
      previews.some((preview) => contentBriefPreviewMatchesDecision(preview, decision))
    ) ??
    topDecisions[0] ??
    data.decision_queue[0];
  const primaryPreview = contentPrimaryBriefPreview(primaryDecision, previews);
  const blockedClaims = uniqueValues([
    ...(primaryPreview?.blocked_claims ?? []),
    ...(primaryDecision?.blocked_claims ?? [])
  ]);
  const missingInputs = uniqueValues([
    ...(primaryPreview?.publication_blocker_labels ?? []),
    ...(primaryPreview?.required_validation_labels ?? [])
  ]);
  const evidenceIds = uniqueValues([
    ...(primaryPreview?.evidence_ids ?? []),
    ...(primaryDecision?.evidence_ids ?? [])
  ]);
  const sourceConnectors = uniqueValues([
    ...(primaryPreview?.source_connectors ?? []),
    ...(primaryDecision?.source_connectors ?? [])
  ]);
  const marketerDecision = data.marketer_decision;
  const panelBlockedClaims = marketerDecision?.blocked_claims ?? blockedClaims;
  const panelMissingInputs = marketerDecision?.missing_inputs ?? missingInputs;
  const panelEvidenceSummary =
    marketerDecision?.evidence_summary ?? formatContentEvidenceCount(evidenceIds.length);
  const panelSourceConnectors = connectorLabelsFromStatuses(
    marketerDecision?.source_connectors ?? sourceConnectors,
    data.connectors
  );
  const panelMeasurementPlan =
    marketerDecision?.measurement_plan ?? contentSelectedMeasurementPlan(primaryPreview);

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
            {primaryPreview?.content_angle ?? primaryDecision.summary ?? primaryDecision.rationale}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          {contentSelectedMetricTiles(primaryDecision, primaryPreview).map(([label, value]) => (
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
              values={primaryPreview?.h1_direction ? [primaryPreview.h1_direction] : []}
              empty="do doprecyzowania w planie treści"
            />
            <TraceLine
              label="H2"
              values={primaryPreview?.h2_direction?.slice(0, 3) ?? []}
              empty="do doprecyzowania w planie treści"
            />
            <TraceLine
              label="FAQ"
              values={primaryPreview?.faq_direction?.slice(0, 3) ?? []}
              empty="do doprecyzowania w planie treści"
            />
            <TraceLine
              label="Wezwanie do działania"
              values={primaryPreview?.cta_direction ? [primaryPreview.cta_direction] : []}
              empty="do doprecyzowania w planie treści"
            />
          </div>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Adresy i podgląd</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            `ekologus.pl` i `sklep.ekologus.pl` są źródłem prawdy. Adres podglądu
            jest opcjonalny i nie jest docelowym adresem SEO.
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
            />
            <TraceLine
              label="Podgląd"
              values={[
                marketerDecision?.preview_url ??
                  primaryPreview?.preview_url ??
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
              values={primaryPreview?.source_facts?.slice(0, 4) ?? []}
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
  const ahrefsWordPressOverlapCount = contentAhrefsWordPressOverlapCount(data);
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
          <MetricTile label="Zapytania/URL" value={data.query_page_count} />
          <MetricTile label="GSC↔WP" value={data.matched_inventory_count} />
          <MetricTile label="Ahrefs↔WP" value={ahrefsWordPressOverlapCount} />
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {topDecisions.length > 0 ? (
            topDecisions.map((decision) => (
              <ContentDecisionCard key={decision.id} decision={decision} connectors={data.connectors} />
            ))
          ) : (
            <BlockerNotice message="Brak decyzji contentowych. Najpierw uruchom odczyt GSC i WordPress." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb treści</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine label="Tryby decyzji" values={summary.decision_type_labels} empty="brak" />
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
              values={[formatContentEvidenceCount(summary.evidence_ids.length)]}
              empty="brak"
            />
            <TraceLine label="Akcje" values={[formatContentActionCount(actionIds.length)]} />
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

function contentAhrefsWordPressOverlapCount(data: ContentDiagnosticsResponse) {
  const ahrefsDecision = data.decision_queue.find(
    (decision) => decision.decision_type === "review_ahrefs_gap_records"
  );
  const value = ahrefsDecision?.metric_tiles?.["WP overlap"];
  return typeof value === "number" ? value : 0;
}

function ContentDecisionCard({
  decision,
  connectors
}: {
  decision: ContentDecisionItem;
  connectors: ConnectorStatus[];
}) {
  const canonicalUrl = decision.final_canonical_url ?? decision.intended_final_url;
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{contentDecisionTitle(decision)}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {decision.decision_type_label || decision.decision_type}
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
            WordPress: {decision.wordpress_match_label ?? decision.wordpress_match}
          </span>
        ) : null}
        {decision.wordpress_match_confidence ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Dopasowanie: {decision.wordpress_match_confidence_label ?? decision.wordpress_match_confidence}
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
            Spis: {decision.inventory_gate_status_label ?? decision.inventory_gate_status}
          </span>
        ) : null}
        {decision.canonical_gate_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Kanoniczny: {decision.canonical_gate_status_label ?? decision.canonical_gate_status}
          </span>
        ) : null}
        {decision.duplicate_gate_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Duplikaty: {decision.duplicate_gate_status_label ?? decision.duplicate_gate_status}
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
                    <div className="mt-0.5 text-xs text-slate-500">
                      {candidate.gap_type_label || candidate.gap_type} /{" "}
                      {candidate.relevance_status_label || candidate.relevance_status} / score{" "}
                      {candidate.relevance_score}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 text-xs">
                    <span className="rounded border border-line bg-white px-2 py-1">
                      GSC: {candidate.gsc_demand_label || candidate.gsc_demand}
                    </span>
                    <span className="rounded border border-line bg-white px-2 py-1">
                      WP: {candidate.wordpress_inventory_match_label || candidate.wordpress_inventory_match}
                    </span>
                  </div>
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-600">{candidate.next_step}</p>
                <TraceLine
                  label="Powody"
                  values={candidate.business_relevance_reason_labels}
                />
                <TraceLine
                  label="Overlap GSC"
                  values={candidate.gsc_overlap_terms.slice(0, 3)}
                />
                <TraceLine
                  label="Overlap WP"
                  values={candidate.wordpress_overlap_urls.map(shortPath).slice(0, 3)}
                />
              </div>
            ))}
          </div>
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Dowody"
          values={[formatContentEvidenceCount(decision.evidence_ids.length)]}
          empty="brak"
        />
        <TraceLine label="Źródła" values={connectorLabelsFromStatuses(decision.source_connectors, connectors)} />
        <TraceLine label="Akcje" values={[formatContentActionCount(decision.action_ids.length)]} />
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
        <TraceLine label="Akcje" values={[formatContentActionCount(data.action_ids.length)]} />
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

function formatContentEvidenceCount(count: number) {
  if (count === 0) return "brak dowodów źródłowych";
  if (count === 1) return "1 dowód źródłowy";
  if (count >= 2 && count <= 4) return `${count} dowody źródłowe`;
  return `${count} dowodów źródłowych`;
}

function formatContentActionCount(count: number) {
  if (count === 0) return "brak";
  if (count === 1) return "1 akcja";
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) {
    return `${count} akcje`;
  }
  return `${count} akcji`;
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

type ContentBriefPreviewPayload = Omit<ContentBriefPreviewItem, "action_id">;

function contentBriefPreviewItemsFromActions(actions: ActionObject[]): ContentBriefPreviewItem[] {
  return actions.flatMap((action) => {
    const rows = action.payload.content_brief_preview;
    if (!Array.isArray(rows)) return [];
    return rows
      .filter(isContentBriefPreviewItem)
      .map((row) => ({ ...row, action_id: action.id }));
  });
}

function contentPrimaryBriefPreview(
  decision: ContentDecisionItem | undefined,
  previews: ContentBriefPreviewItem[]
) {
  if (!decision) return previews[0];
  return previews.find((preview) => contentBriefPreviewMatchesDecision(preview, decision));
}

function contentBriefPreviewMatchesDecision(
  preview: ContentBriefPreviewItem,
  decision: ContentDecisionItem
) {
  return (
    Boolean(preview.source_public_url) &&
    (preview.source_public_url === decision.source_public_url ||
      preview.source_public_url === decision.final_canonical_url ||
      preview.source_public_url === decision.intended_final_url ||
      preview.source_public_url === decision.page)
  );
}

function contentSelectedMetricTiles(
  decision: ContentDecisionItem,
  preview: ContentBriefPreviewItem | undefined
): Array<[string, string | number]> {
  const snapshot = preview?.metric_snapshot ?? {};
  const rawRows: Array<[string, string | number]> = [
    ["Zapytania", contentMetricSnapshotValue(snapshot, "queries")],
    ["Kliknięcia", contentMetricSnapshotValue(snapshot, "clicks")],
    ["Wyświetlenia", contentMetricSnapshotValue(snapshot, "impressions")],
    ["CTR", contentMetricSnapshotValue(snapshot, "ctr")]
  ];
  const rows = rawRows.filter(
    (row): row is [string, string | number] => row[1] !== "brak"
  );
  if (rows.length) return rows;
  return Object.entries(decision.metric_tiles)
    .slice(0, 4)
    .map(([label, value]): [string, string | number] => [label, value]);
}

function contentMetricSnapshotValue(
  snapshot: Record<string, string | number | boolean | null>,
  key: string
) {
  if (!(key in snapshot)) return "brak";
  return contentBriefMetricValue(key, snapshot[key]);
}

function contentSelectedMeasurementPlan(preview: ContentBriefPreviewItem | undefined) {
  if (!preview) {
    return "Najpierw zapisz sprawdzenie planu treści. Bez publikacji oraz danych po publikacji WILQ nie ocenia sukcesu ani porażki.";
  }
  return [
    "Po sprawdzeniu zapisz decyzję contentową i punkt odniesienia z GSC/WordPress.",
    "Po ewentualnym szkicu i publikacji potrzebne są okna sprawdzenia w GSC/GA4.",
    "Do tego czasu WILQ blokuje obietnice pozycji, ruchu, leadów i przychodu."
  ].join(" ");
}

function wordpressDraftPayloadPreviewItemsFromActions(
  actions: ActionObject[]
): WordPressDraftPayloadPreviewItem[] {
  return actions.flatMap((action) => {
    const rows = action.payload.wordpress_draft_payload_preview;
    if (!Array.isArray(rows)) return [];
    return rows
      .filter(isWordPressDraftPayloadPreviewItem)
      .map((row) => ({ ...row, action_id: action.id }));
  });
}

function isContentBriefPreviewItem(value: unknown): value is ContentBriefPreviewPayload {
  if (!isPlainObject(value)) return false;
  return (
    typeof value.candidate_id === "string" &&
    typeof value.source_type === "string" &&
    typeof value.mode === "string" &&
    typeof value.topic === "string" &&
    isPlainObject(value.metric_snapshot) &&
    typeof value.brief_goal === "string" &&
    Array.isArray(value.required_validation) &&
    Array.isArray(value.blocked_claims) &&
    Array.isArray(value.evidence_ids) &&
    typeof value.apply_allowed === "boolean" &&
    typeof value.api_mutation_ready === "boolean"
  );
}

function isWordPressDraftPayloadPreviewItem(
  value: unknown
): value is Omit<WordPressDraftPayloadPreviewItem, "action_id"> {
  if (!isPlainObject(value)) return false;
  return (
    typeof value.preview_contract === "string" &&
    typeof value.candidate_id === "string" &&
    typeof value.operation_type === "string" &&
    typeof value.post_status === "string" &&
    typeof value.topic === "string" &&
    isPlainObject(value.draft_payload) &&
    Array.isArray(value.required_validation) &&
    Array.isArray(value.blocked_claims) &&
    Array.isArray(value.evidence_ids) &&
    typeof value.mutation_allowed === "boolean" &&
    typeof value.apply_allowed === "boolean" &&
    typeof value.api_mutation_ready === "boolean"
  );
}


function contentAddressValues(
  preview: Pick<
    ContentBriefPreviewItem | WordPressDraftPayloadPreviewItem,
    | "source_public_url"
    | "preview_url"
    | "intended_final_url"
    | "final_canonical_url"
  >
) {
  const values: string[] = [];
  const canonicalUrl = preview.final_canonical_url ?? preview.intended_final_url;
  if (preview.source_public_url) {
    values.push(`źródło: ${shortPath(preview.source_public_url)}`);
  }
  if (canonicalUrl) {
    values.push(`kanoniczny: ${shortPath(canonicalUrl)}`);
  }
  if (preview.preview_url) {
    values.push(`podgląd opcjonalny: ${shortPath(preview.preview_url)}`);
  }
  return values;
}

function contentDraftGateValues(
  item: Pick<WordPressDraftPayloadPreviewItem, "content_gate_status_summary">
): string[] {
  return (item.content_gate_status_summary ?? []).filter((value) => value.trim().length > 0);
}

function contentDraftContractValues(
  item: WordPressDraftPayloadPreviewItem
): string[] {
  return (item.draft_generation_summary ?? []).filter((value) => value.trim().length > 0);
}

function contentDraftReadinessReviewValues(
  item: WordPressDraftPayloadPreviewItem
): string[] {
  return (item.draft_readiness_review_summary ?? []).filter(
    (value) => value.trim().length > 0
  );
}

function contentDraftReadinessContractValues(
  item: WordPressDraftPayloadPreviewItem
): string[] {
  return (item.draft_readiness_review_contract_summary ?? []).filter(
    (value) => value.trim().length > 0
  );
}

function contentWordPressDraftHandoffValues(item: WordPressDraftPayloadPreviewItem): string[] {
  return (item.wordpress_draft_handoff_summary ?? []).filter((value) => value.trim().length > 0);
}

function contentWordPressDraftHandoffContractValues(
  item: WordPressDraftPayloadPreviewItem
): string[] {
  return (item.wordpress_draft_handoff_contract_summary ?? []).filter(
    (value) => value.trim().length > 0
  );
}

function contentPostPublicationMeasurementValues(
  item: WordPressDraftPayloadPreviewItem
): string[] {
  return (item.post_publication_measurement_summary ?? []).filter(
    (value) => value.trim().length > 0
  );
}

function contentBriefMetricValue(metricName: string, value: string | number | boolean | null) {
  return formatContentMetricValue(metricName, value);
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
