import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck, RefreshCw, ShieldAlert } from "lucide-react";

import {
  ActionObject,
  ActionReviewRequest,
  ContentDiagnosticsResponse,
  getActions,
  getContentDiagnostics,
  reviewAction
} from "../lib/api";
import { MetricFactChips } from "../components/MetricFactChips";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import {
  ActionObjectFocus,
  ActionObjectIdFocus
} from "./ActionObjectPanels";
import { shortPath } from "./TacticalQueuePanel";

type ContentDecisionItem = ContentDiagnosticsResponse["decision_queue"][number];

export function ContentDiagnosticSurface({ title }: { title: string }) {
  const diagnostics = useQuery({
    queryKey: ["content-diagnostics"],
    queryFn: getContentDiagnostics
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
        <BlockerNotice message="Nie udało się odczytać /api/content/diagnostics. Content route nie może udawać SEO ani content insightów bez WILQ API." />
      </main>
    );
  }

  const data = diagnostics.data;
  const routeActions = (actions.data ?? []).filter((action) => data.action_ids.includes(action.id));
  const latestStatuses = data.latest_refreshes.map(
    (refresh) => `${refresh.connector_id}: ${contentRefreshStatusLabel(refresh.status)}`
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok SEO i treści z WILQ API. Łączy zapytania i URL-e z GSC,
            inventory WordPress i ActionObjecty, żeby marketer wiedział co odświeżyć,
            połączyć, utworzyć albo zablokować bez duplikowania treści.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Zapytania/URL" value={data.query_page_count} />
          <MetricTile label="Dopasowania WP" value={data.matched_inventory_count} />
          <MetricTile label="Dowody" value={data.evidence_ids.length} />
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
            </span>
            {data.connectors.map((connector) => (
              <span
                key={connector.id}
                className="rounded-md border border-line px-2 py-1 text-slate-600"
              >
                {connector.id}: {contentConnectorStatusLabel(connector.status)}
              </span>
            ))}
          </div>
        </div>
        <TraceLine label="Ostatnie odczyty" values={latestStatuses} />
      </section>

      <ContentOperatorSummary data={data} />

      <ContentBriefPreviewPanel actions={routeActions} />

      <ContentDiagnosticProof data={data} />

      <div className="mt-6">
        {actions.isLoading ? (
          <ActionObjectIdFocus
            actionIds={data.action_ids}
            note="Ładuję szczegóły ActionObjectów; decyzje contentowe powyżej są już oparte o WILQ API."
          />
        ) : actions.error ? (
          <ActionObjectIdFocus
            actionIds={data.action_ids}
            note="Nie udało się odczytać pełnych ActionObjectów. Linki do walidacji zostają widoczne, ale payload preview wymaga /api/actions."
          />
        ) : (
          <ActionObjectFocus actions={routeActions} />
        )}
      </div>

      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa treści
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              WILQ może przygotować brief, kolejkę odświeżenia i podgląd payloadu,
              ale nie publikuje ani nie zmienia WordPress bez walidacji ActionObject,
              jawnej zgody operatora i audytu.
            </p>
          </div>
        </div>
        <TraceLine
          label="Zablokowane claimy"
          values={contentBlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
        />
      </section>
    </main>
  );
}

type ContentBriefPreviewItem = {
  action_id: string;
  candidate_id: string;
  source_type: string;
  mode: string;
  topic: string;
  target_url?: string | null;
  source_url?: string | null;
  competitor_domain?: string | null;
  wordpress_inventory_match?: string | null;
  gsc_demand?: string | null;
  metric_snapshot: Record<string, string | number | boolean | null>;
  brief_goal: string;
  required_validation: string[];
  blocked_claims: string[];
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
            Podgląd briefów do review
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            Co WILQ może przygotować bez publikacji
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            To są kandydaci z ActionObject. Każdy wymaga walidacji GSC/WordPress,
            sprawdzenia duplikatów i decyzji operatora przed jakąkolwiek zmianą treści.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs">
          <MetricTile label="Preview" value={previews.length} />
          <MetricTile
            label="Apply"
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
              Payload draftu po review
            </div>
            <h3 className="mt-1 text-sm font-semibold text-ink">
              Co WILQ może przygotować jako szkic WordPress
            </h3>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              Te payloady pojawiają się dopiero po zapisanym review kandydata.
              Status pozostaje `draft`, a mutacje i publikacja są zablokowane.
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
            {contentBriefSourceLabel(preview.source_type)} / {contentBriefModeLabel(preview.mode)}
          </p>
        </div>
        <StatusBadge value={preview.apply_allowed ? "ready" : "blocked"} />
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{preview.brief_goal}</p>
      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        {Object.entries(preview.metric_snapshot).slice(0, 4).map(([label, value]) => (
          <MetricTile
            key={`${preview.candidate_id}-${label}`}
            label={label}
            value={contentBriefMetricValue(value)}
          />
        ))}
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Walidacje" values={preview.required_validation.slice(0, 4)} />
        <TraceLine
          label="Blokady claimów"
          values={contentBlockedClaimLabels(preview.blocked_claims.slice(0, 4))}
        />
        <LinkedTraceLine label="Dowody" values={preview.evidence_ids.slice(0, 3)} kind="evidence" />
        <LinkedTraceLine label="ActionObject" values={[preview.action_id]} kind="actions" />
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
          {reviewMutation.isPending ? "Zapisuję review" : "Zapisz review briefu"}
        </button>
        <span className="text-xs text-slate-600">
          Zapisuje wybór kandydata. Nie publikuje i nie wykonuje apply.
        </span>
      </div>
      {reviewMutation.data ? (
        <p className="mt-2 rounded-md border border-line bg-white p-2 text-xs leading-5 text-slate-600">
          Zapisano review: {reviewMutation.data.audit_event.event_type}. Apply nadal:{" "}
          {reviewMutation.data.review_gate.apply_allowed ? "otwarte" : "zablokowane"}.
        </p>
      ) : null}
      {reviewMutation.error instanceof Error ? (
        <p className="mt-2 text-xs leading-5 text-risk">
          Nie udało się zapisać review: {reviewMutation.error.message}
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
  target_url?: string | null;
  source_url?: string | null;
  draft_payload: {
    post_status?: string;
    post_title?: string;
    post_excerpt_direction?: string;
    content_blocks?: Array<{ section: string; instruction: string }>;
  };
  required_validation: string[];
  blocked_claims: string[];
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
            {preview.draft_payload.post_title ?? `Draft: ${preview.topic}`}
          </h4>
          <p className="mt-0.5 text-xs uppercase tracking-normal text-slate-500">
            {contentDraftOperationLabel(preview.operation_type)} / {preview.post_status}
          </p>
        </div>
        <StatusBadge value={preview.mutation_allowed ? "ready" : "blocked"} />
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-600">
        {preview.draft_payload.post_excerpt_direction ??
          "Szkic payloadu do review. Nie publikuje i nie wykonuje apply."}
      </p>
      {preview.target_url ? (
        <p className="mt-2 text-xs text-slate-600">URL: {shortPath(preview.target_url)}</p>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Bloki"
          values={(preview.draft_payload.content_blocks ?? [])
            .slice(0, 4)
            .map((block) => block.section)}
        />
        <TraceLine label="Walidacje" values={preview.required_validation.slice(0, 4)} />
        <TraceLine
          label="Blokady claimów"
          values={contentBlockedClaimLabels(preview.blocked_claims.slice(0, 4))}
        />
        <LinkedTraceLine label="Dowody" values={preview.evidence_ids.slice(0, 3)} kind="evidence" />
        <LinkedTraceLine label="ActionObject" values={[preview.action_id]} kind="actions" />
      </div>
    </article>
  );
}

function contentBriefReviewRequest(preview: ContentBriefPreviewItem): ActionReviewRequest {
  return {
    outcome: "approved_for_prepare",
    reviewed_by: "operator_local_dashboard",
    notes: `Wybrano kandydata briefu ${preview.candidate_id} (${preview.topic}) do dalszego review. Ten zapis nie publikuje treści i nie wykonuje apply.`,
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

function ContentOperatorSummary({ data }: { data: ContentDiagnosticsResponse }) {
  const decisions = data.decision_queue;
  const topDecisions = decisions
    .slice()
    .sort((left, right) => contentDecisionSortValue(left) - contentDecisionSortValue(right))
    .slice(0, 4);
  const matchedCount = decisions.filter((decision) => decision.wordpress_match === "found").length;
  const missingCount = decisions.filter((decision) => decision.wordpress_match === "missing").length;
  const decisionTypeLabels = Array.from(
    new Set(decisions.map((decision) => contentDecisionTypeLabel(decision.decision_type)))
  );
  const actionIds = data.action_ids.length ? data.action_ids : ["act_prepare_content_refresh_queue"];

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Operator Content
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            Co marketer ma zrobić teraz z treściami
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ łączy zapytania i URL-e z GSC z inventory WordPress. Najpierw obsłuż
            istniejące URL-e i klastry zapytań, potem dopiero twórz nowe treści. Bez
            dowodów nie wolno twierdzić, że wzrosną leady, pozycje albo konwersje.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Zapytania/URL" value={data.query_page_count} />
          <MetricTile label="Dopasowania WP" value={data.matched_inventory_count} />
          <MetricTile label="Decyzje" value={decisions.length} />
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
            <TraceLine label="Tryby decyzji" values={decisionTypeLabels} empty="brak" />
            <TraceLine
              label="Dopasowania WordPress"
              values={[
                `potwierdzone: ${matchedCount}`,
                `brak potwierdzenia: ${missingCount}`
              ]}
            />
            <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 6)} kind="evidence" />
            <LinkedTraceLine label="ActionObject" values={actionIds} kind="actions" />
            <TraceLine
              label="Nie wolno twierdzić"
              values={contentBlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
            />
          </div>
          <a
            href={`/actions/${actionIds[0]}`}
            className="mt-4 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
          >
            Waliduj ActionObject
          </a>
        </div>
      </div>
    </section>
  );
}

function ContentDecisionCard({ decision }: { decision: ContentDecisionItem }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{contentDecisionTitle(decision)}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {contentDecisionTypeLabel(decision.decision_type)}
          </p>
        </div>
        <StatusBadge value={decision.status} />
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
            WordPress: {wordpressMatchLabel(decision.wordpress_match)}
          </span>
        ) : null}
        {decision.wordpress_match_confidence ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Dopasowanie: {wordpressMatchConfidenceLabel(decision.wordpress_match_confidence)}
          </span>
        ) : null}
      </div>
      {decision.ahrefs_candidate_rows.length > 0 ? (
        <div className="mt-3 rounded-md border border-line bg-white p-3">
          <h4 className="text-sm font-semibold text-ink">Kandydaci Ahrefs do review</h4>
          <div className="mt-2 grid gap-2">
            {decision.ahrefs_candidate_rows.slice(0, 3).map((candidate) => (
              <div key={candidate.id} className="rounded border border-line bg-slate-50 p-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-ink">{candidate.topic}</div>
                    <div className="mt-0.5 text-xs text-slate-500">
                      {contentAhrefsGapTypeLabel(candidate.gap_type)} /{" "}
                      {contentAhrefsRelevanceLabel(candidate.relevance_status)} / score{" "}
                      {candidate.relevance_score}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 text-xs">
                    <span className="rounded border border-line bg-white px-2 py-1">
                      GSC: {candidate.gsc_demand === "present" ? "jest" : "brak"}
                    </span>
                    <span className="rounded border border-line bg-white px-2 py-1">
                      WP: {candidate.wordpress_inventory_match === "present" ? "jest" : "brak"}
                    </span>
                  </div>
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-600">{candidate.next_step}</p>
                <TraceLine
                  label="Powody"
                  values={candidate.business_relevance_reasons.map(contentAhrefsReasonLabel)}
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
        <LinkedTraceLine label="Dowody" values={decision.evidence_ids.slice(0, 4)} kind="evidence" />
        <TraceLine label="Źródła" values={decision.source_connectors} />
        <LinkedTraceLine label="Akcje" values={decision.action_ids} kind="actions" />
        <TraceLine label="Nie wolno twierdzić" values={contentBlockedClaimLabels(decision.blocked_claims)} />
      </div>
      {decision.metric_facts.length > 0 ? <MetricFactChips facts={decision.metric_facts.slice(0, 4)} /> : null}
    </article>
  );
}

function ContentDiagnosticProof({ data }: { data: ContentDiagnosticsResponse }) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  const sourceConnectors = uniqueValues([
    ...data.sections.flatMap((section) => section.source_connectors),
    ...data.decision_queue.flatMap((decision) => decision.source_connectors)
  ]);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i ograniczenia Content
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót kontraktu WILQ API. Decyzje dla marketera są powyżej;
            tutaj widać, z jakich źródeł i blokad wynikają.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Sekcje API" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
        </div>
      </div>
      {metricFacts.length > 0 ? <MetricFactChips facts={metricFacts.slice(0, 8)} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={data.sections.map((section) => contentSectionLabel(section.id))} />
        <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 8)} kind="evidence" />
        <TraceLine label="Źródła" values={sourceConnectors} />
        <LinkedTraceLine label="Akcje" values={data.action_ids} kind="actions" />
        <TraceLine
          label="Zablokowane claimy"
          values={contentBlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
        />
      </div>
    </section>
  );
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


function contentBriefSourceLabel(value: string) {
  const labels: Record<string, string> = {
    gsc_query_page: "GSC query/page",
    ahrefs_gap_review: "Ahrefs review"
  };
  return labels[value] ?? value;
}

function contentBriefModeLabel(value: string) {
  const labels: Record<string, string> = {
    refresh: "refresh",
    inventory_check: "sprawdzenie inventory",
    review: "review",
    merge: "merge",
    create: "create",
    block: "block"
  };
  return labels[value] ?? value;
}

function contentDraftOperationLabel(value: string) {
  const labels: Record<string, string> = {
    prepare_existing_content_draft: "draft istniejącej treści",
    prepare_new_content_draft_review: "draft nowej treści do review"
  };
  return labels[value] ?? value;
}

function contentBriefMetricValue(value: string | number | boolean | null) {
  if (typeof value === "boolean") return value ? "tak" : "nie";
  return value ?? "brak";
}

function contentDecisionTypeLabel(decisionType: ContentDecisionItem["decision_type"]) {
  if (decisionType === "refresh_or_merge") return "odświeżenie albo scalenie";
  if (decisionType === "merge_create_after_inventory_check") {
    return "scalenie lub utworzenie po kontroli inventory";
  }
  if (decisionType === "inventory_check_before_create") return "kontrola inventory przed briefem";
  if (decisionType === "review_ahrefs_gap_records") return "review luk Ahrefs";
  return "blokada zadania contentowego";
}

function contentAhrefsGapTypeLabel(value: string) {
  const labels: Record<string, string> = {
    content_gap: "content gap",
    organic_keyword_gap: "keyword gap",
    top_page_gap: "top page",
    backlink_gap: "backlink gap",
    competitor_page: "strona konkurencji"
  };
  return labels[value] ?? value;
}

function contentAhrefsRelevanceLabel(value: string) {
  const labels: Record<string, string> = {
    relevant: "pasuje",
    review: "do sprawdzenia",
    off_topic: "off-topic"
  };
  return labels[value] ?? value;
}

function contentAhrefsReasonLabel(value: string) {
  const labels: Record<string, string> = {
    ekologus_domain_term: "pasuje do zakresu Ekologus",
    relevant_competitor_domain: "istotny konkurent",
    gsc_overlap: "pokrywa się z GSC",
    wordpress_inventory_overlap: "pokrywa się z WordPress",
    content_candidate: "kandydat contentowy",
    backlink_review_only: "tylko review backlinkowe",
    off_topic_phrase: "fraza off-topic",
    off_topic_competitor_domain: "konkurent off-topic",
    broad_backlink_domain: "szeroki backlink"
  };
  return labels[value] ?? value;
}

function contentDecisionSortValue(decision: ContentDecisionItem) {
  const statusRank: Record<ContentDecisionItem["status"], number> = {
    ready: 0,
    blocked: 1
  };
  const riskRank: Record<ContentDecisionItem["risk"], number> = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3
  };
  return statusRank[decision.status] * 1000 + decision.priority * 10 + riskRank[decision.risk];
}

function contentSectionLabel(sectionId: string) {
  if (sectionId === "content_query_page_matrix") return "Zapytania i URL-e z GSC";
  if (sectionId === "content_inventory_match") return "Dopasowanie WordPress";
  if (sectionId === "content_action_safety") return "Bezpieczeństwo akcji";
  return sectionId;
}

function contentConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function contentRefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  if (status === "running") return "w toku";
  return status;
}

function wordpressMatchLabel(value: string) {
  if (value === "found") return "potwierdzony";
  if (value === "missing") return "brak potwierdzenia";
  return value;
}

function wordpressMatchConfidenceLabel(value: string) {
  if (value === "exact_url") return "dokładny URL";
  if (value === "host_alias_sitemap") return "alias hosta z sitemap";
  if (value === "path_fallback") return "dopasowanie ścieżki";
  if (value === "missing") return "brak dopasowania";
  return value;
}

function contentBlockedClaimLabels(claims: string[]) {
  const labels: Record<string, string> = {
    "auto publish": "automatyczna publikacja",
    "content rewrite": "rewrite treści bez dowodu",
    "conversion uplift": "wzrost konwersji",
    "duplicate avoidance": "uniknięcie duplikacji",
    "duplicate-free guarantee": "gwarancja braku duplikatów",
    "lead uplift": "wzrost leadów",
    "merge plan": "plan scalenia",
    "new article without inventory check": "nowy artykuł bez kontroli inventory",
    "ranking guarantee": "gwarancja pozycji",
    "ranking win": "wygrana pozycji",
    "refresh plan": "plan odświeżenia",
    "revenue impact": "wpływ na przychód",
    "ROAS": "ROAS",
    "wordpress write": "zapis do WordPress"
  };
  return uniqueValues(claims.map((claim) => labels[claim] ?? claim));
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
