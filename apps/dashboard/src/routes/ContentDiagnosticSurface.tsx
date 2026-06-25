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
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import {
  ActionObjectFocus,
  ActionObjectIdFocus
} from "./ActionObjectPanels";
import { shortPath } from "./TacticalQueuePanel";

type ContentDecisionItem = ContentDiagnosticsResponse["decision_queue"][number];
type ContentMetricFact = ContentDiagnosticsResponse["sections"][number]["metric_facts"][number];

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
  const ahrefsWordPressOverlapCount = contentAhrefsWordPressOverlapCount(data);
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
            inventory WordPress i akcje do walidacji, żeby marketer wiedział co odświeżyć,
            połączyć, utworzyć albo zablokować bez duplikowania treści.
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

      <ContentSelectedDecisionPanel data={data} actions={routeActions} />

      <ContentOperatorSummary data={data} />

      <ContentBriefPreviewPanel actions={routeActions} />

      <ContentDiagnosticProof data={data} />

      <div className="mt-6">
        {actions.isLoading ? (
          <ActionObjectIdFocus
            actionIds={data.action_ids}
            note="Ładuję szczegóły akcji; decyzje contentowe powyżej są już oparte o WILQ API."
          />
        ) : actions.error ? (
          <ActionObjectIdFocus
            actionIds={data.action_ids}
            note="Nie udało się odczytać pełnych akcji. Linki do walidacji zostają widoczne, ale podgląd payloadu wymaga /api/actions."
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
              ale nie publikuje ani nie zmienia WordPress bez walidacji akcji,
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
  target_site_url?: string | null;
  target_site_host?: string | null;
  source_site_host?: string | null;
  target_site_adaptation_status?: string | null;
  target_site_migration_candidate_url?: string | null;
  target_site_migration_status?: string | null;
  target_site_migration_candidate_inventory_status?: string | null;
  target_site_migration_candidate_inventory_summary?: string | null;
  target_site_alternative_candidate_urls?: string[];
  target_site_alternative_candidate_summary?: string | null;
  target_site_mapping_review_status?: string | null;
  target_site_mapping_review_summary?: string | null;
  target_site_mapping_review_candidate_urls?: string[];
  target_site_review_requirements?: string[];
  target_site_inventory_content_type?: string | null;
  target_site_inventory_status?: string | null;
  target_site_inventory_source?: string | null;
  target_site_inventory_modified_gmt?: string | null;
  target_site_inventory_title_or_h1?: string | null;
  target_site_inventory_canonical_url?: string | null;
  target_site_inventory_missing_fields?: string[];
  target_site_inventory_summary?: string | null;
  inventory_gate_status?: string | null;
  canonical_gate_status?: string | null;
  duplicate_gate_status?: string | null;
  content_gate_summary?: string | null;
  competitor_domain?: string | null;
  wordpress_inventory_match?: string | null;
  gsc_demand?: string | null;
  metric_snapshot: Record<string, string | number | boolean | null>;
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
  publication_blockers?: string[];
  source_facts?: string[];
  missing_evidence?: string[];
  forbidden_claims?: string[];
  required_validation: string[];
  blocked_claims: string[];
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
            Podgląd briefów do review
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            Co WILQ może przygotować bez publikacji
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            To są kandydaci z akcji WILQ. Każdy wymaga walidacji GSC/WordPress,
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
            label={label}
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
          label="Strona docelowa"
          values={contentTargetSiteValues(preview)}
          empty="brak"
        />
        <TraceLine
          label="Review targetu"
          values={(preview.target_site_review_requirements ?? []).slice(0, 4)}
        />
        <TraceLine
          label="Inventory targetu"
          values={contentTargetInventoryValues(preview)}
          empty="brak"
        />
        <TraceLine
          label="Braki targetu"
          values={(preview.target_site_inventory_missing_fields ?? []).slice(0, 6)}
          empty="brak"
        />
        <TraceLine
          label="Status publikacji"
          values={
            preview.publication_readiness_status
              ? [contentPublicationReadinessLabel(preview.publication_readiness_status)]
              : []
          }
          empty="brak"
        />
        <TraceLine
          label="Blockery publikacji"
          values={(preview.publication_blockers ?? []).slice(0, 6)}
          empty="brak"
        />
        <TraceLine
          label="Review prawny"
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
        <TraceLine label="Walidacje" values={preview.required_validation.slice(0, 4)} />
        <TraceLine
          label="Zakazane claimy"
          values={contentBlockedClaimLabels(
            (preview.forbidden_claims ?? preview.blocked_claims).slice(0, 4)
          )}
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
  intent?: string | null;
  target_url?: string | null;
  source_url?: string | null;
  target_site_url?: string | null;
  target_site_host?: string | null;
  source_site_host?: string | null;
  target_site_adaptation_status?: string | null;
  target_site_migration_candidate_url?: string | null;
  target_site_migration_status?: string | null;
  target_site_migration_summary?: string | null;
  target_site_migration_candidate_inventory_status?: string | null;
  target_site_migration_candidate_inventory_summary?: string | null;
  target_site_alternative_candidate_urls?: string[];
  target_site_alternative_candidate_summary?: string | null;
  target_site_mapping_review_status?: string | null;
  target_site_mapping_review_summary?: string | null;
  target_site_mapping_review_candidate_urls?: string[];
  target_site_review_requirements?: string[];
  target_site_inventory_content_type?: string | null;
  target_site_inventory_status?: string | null;
  target_site_inventory_source?: string | null;
  target_site_inventory_modified_gmt?: string | null;
  target_site_inventory_title_or_h1?: string | null;
  target_site_inventory_canonical_url?: string | null;
  target_site_inventory_missing_fields?: string[];
  target_site_inventory_summary?: string | null;
  inventory_gate_status?: string | null;
  canonical_gate_status?: string | null;
  duplicate_gate_status?: string | null;
  content_gate_summary?: string | null;
  draft_generation_status?: string | null;
  draft_blockers?: string[];
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
  draft_readiness_review_contract?: {
    contract_version?: string;
    scope?: string;
    allowed_outcomes?: string[];
    required_fields?: string[];
    blocked_outputs?: string[];
  };
  draft_readiness_review_recorded_outcome?: string | null;
  canonical_review_recorded_outcome?: string | null;
  duplicate_review_recorded_outcome?: string | null;
  legal_factual_review_recorded_outcome?: string | null;
  human_review_recorded_outcome?: string | null;
  draft_readiness_review_notes?: string | null;
  staging_handoff_status?: string | null;
  staging_handoff_blockers?: string[];
  staging_handoff_contract?: {
    contract_version?: string;
    scope?: string;
    target_site_url?: string | null;
    status?: string;
    blocked_until?: string[];
    requires_passed_gates?: string[];
    required_next_action_contract?: string;
    blocked_outputs?: string[];
  };
  post_publication_measurement_plan?: {
    contract_version?: string;
    scope?: string;
    target_site_url?: string | null;
    status?: string;
    baseline_window?: string;
    followup_windows?: string[];
    required_source_connectors?: string[];
    required_metric_groups?: string[];
    requires_before_claims?: string[];
    blocked_outputs?: string[];
  };
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
      {preview.draft_generation_status ? (
        <p className="mt-2 rounded border border-line bg-white px-3 py-2 text-xs font-medium text-ink">
          Status draftu: {contentDraftGenerationStatusLabel(preview.draft_generation_status)}
        </p>
      ) : null}
      <p className="mt-2 text-xs leading-5 text-slate-600">
        {preview.draft_payload.post_excerpt_direction ??
          "Szkic payloadu do review. Nie publikuje i nie wykonuje apply."}
      </p>
      {preview.intent ? (
        <p className="mt-2 text-xs text-slate-600">Intencja draftu: {preview.intent}</p>
      ) : null}
      {preview.target_url ? (
        <p className="mt-2 text-xs text-slate-600">URL: {shortPath(preview.target_url)}</p>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Strona docelowa"
          values={contentTargetSiteValues(preview)}
          empty="brak"
        />
        <TraceLine
          label="Review targetu"
          values={(preview.target_site_review_requirements ?? []).slice(0, 4)}
        />
        <TraceLine
          label="Inventory targetu"
          values={contentTargetInventoryValues(preview)}
          empty="brak"
        />
        <TraceLine
          label="Braki targetu"
          values={(preview.target_site_inventory_missing_fields ?? []).slice(0, 6)}
          empty="brak"
        />
        <TraceLine label="Gate treści" values={contentDraftGateValues(preview)} empty="brak" />
        <TraceLine
          label="Blockery draftu"
          values={(preview.draft_blockers ?? []).slice(0, 6)}
          empty="brak"
        />
        <TraceLine
          label="Kontrakt draftu"
          values={contentDraftContractValues(preview.draft_generation_contract)}
          empty="brak"
        />
        <TraceLine
          label="Review readiness"
          values={contentDraftReadinessReviewValues(preview)}
          empty="brak zapisu"
        />
        <TraceLine
          label="Kontrakt review"
          values={contentDraftReadinessContractValues(preview.draft_readiness_review_contract)}
          empty="brak"
        />
        <TraceLine
          label="Staging handoff"
          values={contentStagingHandoffValues(preview)}
          empty="brak"
        />
        <TraceLine
          label="Kontrakt stagingu"
          values={contentStagingHandoffContractValues(preview.staging_handoff_contract)}
          empty="brak"
        />
        <TraceLine
          label="Pomiar po publikacji"
          values={contentPostPublicationMeasurementValues(
            preview.post_publication_measurement_plan
          )}
          empty="brak"
        />
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

function ContentSelectedDecisionPanel({
  data,
  actions
}: {
  data: ContentDiagnosticsResponse;
  actions: ActionObject[];
}) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const primaryDecision =
    summary.top_decision_ids
      .map((decisionId) => decisionsById.get(decisionId))
      .find((decision): decision is ContentDecisionItem => Boolean(decision)) ??
    data.decision_queue[0];
  const migrationItem = primaryDecision
    ? summary.target_site_migration_map.find((item) => item.decision_id === primaryDecision.id)
    : undefined;
  const mappingReviewInput = primaryDecision
    ? summary.target_site_mapping_review_inputs.find((item) => item.decision_id === primaryDecision.id)
    : undefined;
  const previews = contentBriefPreviewItemsFromActions(actions);
  const primaryPreview = contentPrimaryBriefPreview(primaryDecision, migrationItem, previews);
  const blockedClaims = uniqueValues([
    ...(primaryPreview?.blocked_claims ?? []),
    ...(primaryDecision?.blocked_claims ?? []),
    ...(migrationItem?.blocked_outputs ?? []),
    ...(mappingReviewInput?.blocked_outputs ?? [])
  ]);
  const missingInputs = uniqueValues([
    ...(primaryPreview?.publication_blockers ?? []),
    ...(primaryPreview?.required_validation ?? []),
    ...(mappingReviewInput?.required_checked_items ?? [])
  ]);
  const evidenceIds = uniqueValues([
    ...(primaryPreview?.evidence_ids ?? []),
    ...(primaryDecision?.evidence_ids ?? []),
    ...(migrationItem?.evidence_ids ?? [])
  ]);
  const sourceConnectors = uniqueValues([
    ...(primaryPreview?.source_connectors ?? []),
    ...(primaryDecision?.source_connectors ?? []),
    ...(migrationItem?.source_connectors ?? [])
  ]);

  if (!primaryDecision) {
    return (
      <section className="mb-6 rounded-md border border-action/30 bg-action/5 p-4">
        <h2 className="text-base font-semibold tracking-normal text-ink">
          Dzisiejszy brief do review
        </h2>
        <BlockerNotice message="Brak decyzji contentowych. Najpierw odśwież GSC, WordPress i Ahrefs przez WILQ API." />
      </section>
    );
  }

  return (
    <section className="mb-6 rounded-md border border-action/30 bg-action/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-action">
            Dzisiejszy brief do review
          </div>
          <h2 className="mt-1 text-lg font-semibold tracking-normal text-ink">
            Wybrany temat do przeniesienia lub odświeżenia
          </h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
            {contentDecisionTitle(primaryDecision)}.{" "}
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
          <p className="mt-2 text-sm leading-6 text-slate-700">{primaryDecision.rationale}</p>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny następny krok</h3>
          <p className="mt-2 text-sm font-medium leading-6 text-ink">
            {mappingReviewInput?.review_notes_prompt ?? primaryDecision.next_step}
          </p>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Kierunek treści</h3>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine
              label="H1"
              values={primaryPreview?.h1_direction ? [primaryPreview.h1_direction] : []}
              empty="do doprecyzowania w briefie"
            />
            <TraceLine
              label="H2"
              values={primaryPreview?.h2_direction?.slice(0, 3) ?? []}
              empty="do doprecyzowania w briefie"
            />
            <TraceLine
              label="FAQ"
              values={primaryPreview?.faq_direction?.slice(0, 3) ?? []}
              empty="do doprecyzowania w briefie"
            />
            <TraceLine
              label="Wezwanie do działania"
              values={primaryPreview?.cta_direction ? [primaryPreview.cta_direction] : []}
              empty="do doprecyzowania w briefie"
            />
          </div>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Target i mapowanie</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            `ekologus.pl` i `sklep.ekologus.pl` są źródłem prawdy oraz inventory treści.
            `ekologus.dev.proudsite.pl` jest preview/design contextem dla przyszłego
            mapowania, nie źródłem historycznych metryk.
          </p>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine
              label="Źródło"
              values={[primaryDecision.source_url ?? primaryDecision.page ?? ""].filter(Boolean).map(shortPath)}
            />
            <TraceLine
              label="Preview"
              values={[
                migrationItem?.migration_candidate_url ??
                  primaryPreview?.target_site_migration_candidate_url ??
                  primaryPreview?.target_site_url ??
                  ""
              ].filter(Boolean).map(shortPath)}
              empty="brak targetu"
            />
            <TraceLine
              label="Review"
              values={[
                migrationItem?.mapping_review_status
                  ? mappingReviewStatusLabel(migrationItem.mapping_review_status)
                  : "",
                primaryDecision.target_site_mapping_review_status
                  ? mappingReviewStatusLabel(primaryDecision.target_site_mapping_review_status)
                  : "",
                migrationItem?.next_required_gate ? contentNextGateLabel(migrationItem.next_required_gate) : ""
              ].filter(Boolean)}
            />
          </div>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Dowody i źródła</h3>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine label="Dowody" values={[formatContentEvidenceCount(evidenceIds.length)]} />
            <TraceLine label="Źródła" values={sourceConnectors} />
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
              values={contentBlockedClaimLabels(blockedClaims).slice(0, 6)}
            />
            <TraceLine label="Brakuje" values={missingInputs.slice(0, 6)} />
          </div>
        </div>
      </div>

      <div className="mt-3 rounded-md border border-line bg-white p-3">
        <h3 className="text-sm font-semibold text-ink">Jak później sprawdzimy efekt</h3>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {contentSelectedMeasurementPlan(primaryPreview)}
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
            Operator Content
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
              <ContentDecisionCard key={decision.id} decision={decision} />
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
              label="Nowa strona"
              values={[
                summary.target_site_host
                  ? `target: ${summary.target_site_host}`
                  : "target: brak",
                `alias targetu: ${summary.target_site_alias_match_count}`,
                `obecny URL: ${summary.current_site_match_count}`,
                `do mapowania: ${summary.target_site_mapping_review_count}`,
                `kandydat potwierdzony: ${summary.target_site_confirmed_candidate_inventory_count}`,
                `kandydat niepotwierdzony: ${summary.target_site_missing_candidate_inventory_count}`,
                `status: ${contentTargetSiteMappingStatusLabel(
                  summary.target_site_mapping_status
                )}`
              ]}
            />
            {summary.target_site_migration_map.length > 0 ? (
              <div className="rounded border border-line bg-white px-3 py-2">
                <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  Mapa migracji do review
                </div>
                <div className="mt-2 grid gap-2">
                  {summary.target_site_migration_map.slice(0, 4).map((item) => (
                    <div key={item.decision_id} className="grid gap-1 text-xs text-slate-700">
                      <div className="font-medium text-ink">{item.title}</div>
                      <div>
                        {item.source_url ? shortPath(item.source_url) : "brak source URL"} {"->"}{" "}
                        {item.migration_candidate_url
                          ? shortPath(item.migration_candidate_url)
                          : "brak target URL"}
                      </div>
                      <div className="text-slate-500">
                        {item.mapping_review_status
                          ? mappingReviewStatusLabel(item.mapping_review_status)
                          : "review mapowania"}{" "}
                        · {contentNextGateLabel(item.next_required_gate)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            {summary.target_site_mapping_review_inputs.length > 0 ? (
              <div className="rounded border border-line bg-white px-3 py-2">
                <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  Input do review mapowania
                </div>
                <div className="mt-2 grid gap-2">
                  {summary.target_site_mapping_review_inputs.slice(0, 4).map((item) => (
                    <div key={item.decision_id} className="grid gap-1 text-xs text-slate-700">
                      <div className="font-medium text-ink">{item.title}</div>
                      <div>
                        Kandydat: {item.candidate_id}; outcome:{" "}
                        {item.allowed_outcomes.slice(0, 3).join(", ") || "brak"}
                      </div>
                      <div>
                        Target:{" "}
                        {item.candidate_target_urls.slice(0, 2).map(shortPath).join(", ") ||
                          "wymaga ręcznego URL"}
                      </div>
                      <div>
                        Review: zapisz review mapowania przez ActionObject
                      </div>
                      <div>
                        Payload:{" "}
                        {Array.isArray(item.review_payload_template.checked_items)
                          ? `${item.review_payload_template.checked_items.length} checked items`
                          : "template review-only"}
                      </div>
                      <div className="text-slate-500">{item.review_notes_prompt}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            <TraceLine
              label="Dowody"
              values={[formatContentEvidenceCount(summary.evidence_ids.length)]}
              empty="brak"
            />
            <TraceLine label="Akcje" values={[formatContentActionCount(actionIds.length)]} />
            <TraceLine
              label="Nie wolno twierdzić"
              values={contentBlockedClaimLabels(summary.blocked_claims)}
            />
          </div>
          {actionIds.length > 0 ? (
            <a
              href={`/actions/${actionIds[0]}`}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
            >
              Waliduj akcję
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

function contentTargetSiteMappingStatusLabel(status?: string | null) {
  if (status === "target_site_inventory_confirmed") {
    return "inventory targetu potwierdzone";
  }
  if (status === "target_site_mapping_review_needed") {
    return "wymaga mapowania";
  }
  if (status === "current_site_inventory_confirmed") {
    return "potwierdzono obecną stronę";
  }
  return "brak mapowania targetu";
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
        {decision.target_site_adaptation_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Target: {contentTargetSiteStatusLabel(decision.target_site_adaptation_status)}
          </span>
        ) : null}
        {decision.target_site_url ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Docelowo: {shortPath(decision.target_site_url)}
          </span>
        ) : null}
        {decision.target_site_migration_candidate_url ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Migracja: {shortPath(decision.target_site_migration_candidate_url)}
          </span>
        ) : null}
        {decision.target_site_migration_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Mapowanie: {contentTargetSiteMigrationStatusLabel(
              decision.target_site_migration_status
            )}
          </span>
        ) : null}
        {decision.target_site_migration_candidate_inventory_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Kandydat: {candidateInventoryStatusLabel(
              decision.target_site_migration_candidate_inventory_status
            )}
          </span>
        ) : null}
        {decision.target_site_inventory_source ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Inventory: {decision.target_site_inventory_source}
          </span>
        ) : null}
        {decision.inventory_gate_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Inventory gate: {contentGateStatusLabel(decision.inventory_gate_status)}
          </span>
        ) : null}
        {decision.canonical_gate_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Canonical: {contentGateStatusLabel(decision.canonical_gate_status)}
          </span>
        ) : null}
        {decision.duplicate_gate_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Duplikaty: {contentGateStatusLabel(decision.duplicate_gate_status)}
          </span>
        ) : null}
      </div>
      {decision.content_gate_summary ? (
        <p className="mt-2 rounded border border-line bg-white px-3 py-2 text-xs text-slate-700">
          {decision.content_gate_summary}
        </p>
      ) : null}
      {decision.target_site_migration_summary ? (
        <p className="mt-2 rounded border border-line bg-white px-3 py-2 text-xs text-slate-700">
          {decision.target_site_migration_summary}
        </p>
      ) : null}
      {decision.target_site_migration_candidate_inventory_summary ? (
        <p className="mt-2 rounded border border-line bg-white px-3 py-2 text-xs text-slate-700">
          {decision.target_site_migration_candidate_inventory_summary}
        </p>
      ) : null}
      {decision.target_site_alternative_candidate_summary ? (
        <p className="mt-2 rounded border border-line bg-white px-3 py-2 text-xs text-slate-700">
          {decision.target_site_alternative_candidate_summary}
        </p>
      ) : null}
      {decision.target_site_alternative_candidate_urls?.length ? (
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
          {decision.target_site_alternative_candidate_urls.slice(0, 3).map((url) => (
            <span key={url} className="rounded border border-line bg-white px-2 py-1">
              Alternatywa: {shortPath(url)}
            </span>
          ))}
        </div>
      ) : null}
      {decision.target_site_mapping_review_status ? (
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
          <span className="rounded border border-line bg-white px-2 py-1">
            Review mapowania: {mappingReviewStatusLabel(decision.target_site_mapping_review_status)}
          </span>
          {decision.target_site_mapping_review_candidate_urls?.slice(0, 3).map((url) => (
            <span key={url} className="rounded border border-line bg-white px-2 py-1">
              Do review: {shortPath(url)}
            </span>
          ))}
        </div>
      ) : null}
      {decision.target_site_mapping_review_summary ? (
        <p className="mt-2 rounded border border-line bg-white px-3 py-2 text-xs text-slate-700">
          {decision.target_site_mapping_review_summary}
        </p>
      ) : null}
      {decision.target_site_inventory_summary ? (
        <p className="mt-2 rounded border border-line bg-white px-3 py-2 text-xs text-slate-700">
          {decision.target_site_inventory_summary}
        </p>
      ) : null}
      {decision.target_site_inventory_title_or_h1 || decision.target_site_inventory_canonical_url ? (
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
          {decision.target_site_inventory_title_or_h1 ? (
            <span className="rounded border border-line bg-white px-2 py-1">
              Tytuł/H1: {decision.target_site_inventory_title_or_h1}
            </span>
          ) : null}
          {decision.target_site_inventory_canonical_url ? (
            <span className="rounded border border-line bg-white px-2 py-1">
              Canonical: {shortPath(decision.target_site_inventory_canonical_url)}
            </span>
          ) : null}
        </div>
      ) : null}
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
        <TraceLine
          label="Dowody"
          values={[formatContentEvidenceCount(decision.evidence_ids.length)]}
          empty="brak"
        />
        <TraceLine label="Źródła" values={decision.source_connectors} />
        <TraceLine label="Akcje" values={[formatContentActionCount(decision.action_ids.length)]} />
        <TraceLine label="Nie wolno twierdzić" values={contentBlockedClaimLabels(decision.blocked_claims)} />
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
  const visibleEvidenceIds = data.evidence_ids.slice(0, 3);
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
          <MetricTile label="Łącznie dowodów" value={data.evidence_ids.length} />
        </div>
      </div>
      {visibleMetricFacts.length > 0 ? <ContentMetricTiles facts={visibleMetricFacts} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={data.sections.map((section) => contentSectionLabel(section.id))} />
        <LinkedTraceLine label="Przykładowe dowody" values={visibleEvidenceIds} kind="evidence" />
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

function ContentMetricTiles({ facts }: { facts: ContentMetricFact[] }) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
      {facts.map((fact, index) => (
        <MetricTile
          key={`${fact.source_connector}-${fact.name}-${fact.evidence_id}-${index}`}
          label={contentMetricFactLabel(fact.name)}
          value={formatContentMetricValue(fact.name, fact.value)}
        />
      ))}
    </div>
  );
}

function contentMetricFactLabel(metricName: string) {
  const labels: Record<string, string> = {
    ahrefs_content_gap_count: "Luki Ahrefs",
    average_position: "Pozycja",
    clicks: "Kliknięcia",
    content_object_count: "Obiekty WP",
    ctr: "CTR",
    impressions: "Wyświetlenia",
    pages_total: "Strony WP",
    posts_total: "Wpisy WP"
  };
  return labels[metricName] ?? metricName;
}

export function formatContentMetricValue(
  metricName: string,
  value: string | number | boolean | null
) {
  if (typeof value === "boolean") return value ? "tak" : "nie";
  if (value === null) return "brak";
  const numericValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numericValue)) return value;
  if (metricName === "ctr" || metricName === "engagement_rate") {
    return `${formatNumber(numericValue * 100, 2)}%`;
  }
  if (metricName === "average_position") {
    return formatNumber(numericValue, 2);
  }
  if (Number.isInteger(numericValue)) return numericValue.toLocaleString("pl-PL");
  return formatNumber(numericValue, 2);
}

function formatContentEvidenceCount(count: number) {
  if (count === 0) return "brak";
  if (count === 1) return "1 ID";
  return `${count} ID`;
}

function formatContentActionCount(count: number) {
  if (count === 0) return "brak";
  if (count === 1) return "1 akcja";
  return `${count} akcji`;
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
  migrationItem:
    | ContentDiagnosticsResponse["operator_summary"]["target_site_migration_map"][number]
    | undefined,
  previews: ContentBriefPreviewItem[]
) {
  if (!decision) return previews[0];
  return (
    previews.find((preview) => preview.candidate_id === migrationItem?.candidate_id) ??
    previews.find(
      (preview) =>
        Boolean(preview.source_url) &&
        (preview.source_url === decision.source_url ||
          preview.source_url === decision.page ||
          preview.source_url === decision.wordpress_content_url)
    ) ??
    previews.find(
      (preview) =>
        Boolean(preview.target_site_migration_candidate_url) &&
        preview.target_site_migration_candidate_url ===
          decision.target_site_migration_candidate_url
    ) ??
    previews[0]
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
    return "Najpierw zapisz review mapowania i briefu. Bez zatwierdzonego mapowania, publikacji oraz danych follow-up WILQ nie ocenia sukcesu ani porażki.";
  }
  return [
    "Po review zapisz decyzję mapowania i baseline z GSC/WordPress.",
    "Po ewentualnym draft/staging/publish potrzebne są follow-up windows w GSC/GA4.",
    "Do tego czasu WILQ blokuje claimy o pozycjach, ruchu, leadach i revenue."
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

function contentDraftGenerationStatusLabel(value: string) {
  const labels: Record<string, string> = {
    ready_for_review: "gotowy tylko do review",
    blocked_pending_target_mapping: "zablokowany do mapowania targetu",
    blocked_pending_canonical_duplicate_review: "zablokowany do canonical i duplikatów",
    blocked_missing_target_inventory: "zablokowany bez inventory targetu",
    blocked_until_content_review: "zablokowany do review treści"
  };
  return labels[value] ?? value;
}

function contentPublicationReadinessLabel(value: string) {
  const labels: Record<string, string> = {
    blocked_until_review: "zablokowane do review"
  };
  return labels[value] ?? value;
}

function contentTargetSiteValues(
  preview: Pick<
    ContentBriefPreviewItem | WordPressDraftPayloadPreviewItem,
    | "source_site_host"
    | "target_site_host"
    | "target_site_url"
    | "target_site_adaptation_status"
    | "target_site_migration_candidate_url"
    | "target_site_migration_status"
    | "target_site_migration_candidate_inventory_status"
    | "target_site_alternative_candidate_urls"
    | "target_site_alternative_candidate_summary"
    | "target_site_mapping_review_status"
    | "target_site_mapping_review_summary"
    | "target_site_mapping_review_candidate_urls"
  >
) {
  const values: string[] = [];
  if (preview.source_site_host && preview.target_site_host) {
    values.push(`${preview.source_site_host} -> ${preview.target_site_host}`);
  } else if (preview.target_site_host) {
    values.push(preview.target_site_host);
  }
  if (preview.target_site_adaptation_status) {
    values.push(contentTargetSiteStatusLabel(preview.target_site_adaptation_status));
  }
  if (preview.target_site_url) {
    values.push(shortPath(preview.target_site_url));
  }
  if (preview.target_site_migration_candidate_url) {
    values.push(`migracja: ${shortPath(preview.target_site_migration_candidate_url)}`);
  }
  if (preview.target_site_migration_status) {
    values.push(contentTargetSiteMigrationStatusLabel(preview.target_site_migration_status));
  }
  if (preview.target_site_migration_candidate_inventory_status) {
    values.push(
      candidateInventoryStatusLabel(preview.target_site_migration_candidate_inventory_status)
    );
  }
  if (preview.target_site_alternative_candidate_urls?.length) {
    values.push(
      `alternatywy: ${preview.target_site_alternative_candidate_urls
        .slice(0, 3)
        .map(shortPath)
        .join(", ")}`
    );
  } else if (preview.target_site_alternative_candidate_summary) {
    values.push(preview.target_site_alternative_candidate_summary);
  }
  if (preview.target_site_mapping_review_status) {
    values.push(`review: ${mappingReviewStatusLabel(preview.target_site_mapping_review_status)}`);
  }
  if (preview.target_site_mapping_review_candidate_urls?.length) {
    values.push(
      `do review: ${preview.target_site_mapping_review_candidate_urls
        .slice(0, 3)
        .map(shortPath)
        .join(", ")}`
    );
  } else if (preview.target_site_mapping_review_summary) {
    values.push(preview.target_site_mapping_review_summary);
  }
  return values;
}

function contentTargetInventoryValues(
  preview: Pick<
    ContentBriefPreviewItem | WordPressDraftPayloadPreviewItem,
    | "target_site_inventory_content_type"
    | "target_site_inventory_status"
    | "target_site_inventory_source"
    | "target_site_inventory_modified_gmt"
    | "target_site_inventory_title_or_h1"
    | "target_site_inventory_canonical_url"
    | "target_site_inventory_summary"
  >
) {
  const values: string[] = [];
  if (preview.target_site_inventory_content_type) {
    values.push(`typ: ${preview.target_site_inventory_content_type}`);
  }
  if (preview.target_site_inventory_status) {
    values.push(`status: ${preview.target_site_inventory_status}`);
  }
  if (preview.target_site_inventory_source) {
    values.push(`źródło: ${preview.target_site_inventory_source}`);
  }
  if (preview.target_site_inventory_modified_gmt) {
    values.push(`modified: ${preview.target_site_inventory_modified_gmt}`);
  }
  if (preview.target_site_inventory_title_or_h1) {
    values.push(`tytuł/H1: ${preview.target_site_inventory_title_or_h1}`);
  }
  if (preview.target_site_inventory_canonical_url) {
    values.push(`canonical: ${shortPath(preview.target_site_inventory_canonical_url)}`);
  }
  if (!values.length && preview.target_site_inventory_summary) {
    values.push(preview.target_site_inventory_summary);
  }
  return values;
}

function contentTargetSiteStatusLabel(value: string) {
  const labels: Record<string, string> = {
    current_site_match: "bieżąca strona",
    target_site_alias_match: "dopasowanie do nowej strony",
    needs_inventory_match: "wymaga dopasowania inventory"
  };
  return labels[value] ?? value;
}

function contentTargetSiteMigrationStatusLabel(value: string) {
  const labels: Record<string, string> = {
    confirmed_target_inventory: "target potwierdzony",
    needs_review: "wymaga mapowania",
    blocked_missing_inventory: "blokada inventory",
    not_applicable: "nie dotyczy"
  };
  return labels[value] ?? value;
}

function candidateInventoryStatusLabel(value: string) {
  const labels: Record<string, string> = {
    confirmed_target_inventory: "kandydat w inventory",
    missing_target_inventory: "kandydat niepotwierdzony",
    not_applicable: "brak kandydata"
  };
  return labels[value] ?? value;
}

function mappingReviewStatusLabel(value: string) {
  const labels: Record<string, string> = {
    confirm_exact_candidate: "potwierdź exact candidate",
    review_alternative_candidates: "przejrzyj alternatywy",
    manual_mapping_required: "wymagane ręczne mapowanie",
    not_applicable: "nie dotyczy"
  };
  return labels[value] ?? value;
}

function contentNextGateLabel(value: string) {
  const labels: Record<string, string> = {
    target_site_mapping_review: "następnie: mapowanie targetu",
    target_site_canonical_review: "następnie: canonical",
    duplicate_or_cannibalization_check: "następnie: duplikaty"
  };
  return labels[value] ?? `następnie: ${value}`;
}

function contentDraftGateValues(
  item: Pick<
    ContentBriefPreviewItem,
    | "inventory_gate_status"
    | "canonical_gate_status"
    | "duplicate_gate_status"
    | "content_gate_summary"
  >
): string[] {
  return [
    item.inventory_gate_status ? `inventory: ${contentGateStatusLabel(item.inventory_gate_status)}` : "",
    item.canonical_gate_status ? `canonical: ${contentGateStatusLabel(item.canonical_gate_status)}` : "",
    item.duplicate_gate_status ? `duplikaty: ${contentGateStatusLabel(item.duplicate_gate_status)}` : "",
    item.content_gate_summary ?? ""
  ].filter((value) => value.trim().length > 0);
}

function contentDraftContractValues(
  contract: WordPressDraftPayloadPreviewItem["draft_generation_contract"]
): string[] {
  if (!contract) return [];
  return [
    contract.contract_version ? `contract: ${contract.contract_version}` : "",
    contract.allowed_output_kind ? `output: ${contentDraftOutputKindLabel(contract.allowed_output_kind)}` : "",
    ...(contract.requires_passed_gates ?? []).slice(0, 3).map((value) => `gate: ${value}`),
    ...(contract.forbidden_outputs ?? []).slice(0, 3).map((value) => `zakaz: ${value}`)
  ].filter((value) => value.trim().length > 0);
}

function contentDraftReadinessReviewValues(
  item: WordPressDraftPayloadPreviewItem
): string[] {
  return [
    item.draft_readiness_review_recorded_outcome
      ? `draft: ${item.draft_readiness_review_recorded_outcome}`
      : "",
    item.canonical_review_recorded_outcome
      ? `canonical: ${item.canonical_review_recorded_outcome}`
      : "",
    item.duplicate_review_recorded_outcome
      ? `duplikaty: ${item.duplicate_review_recorded_outcome}`
      : "",
    item.legal_factual_review_recorded_outcome
      ? `legal/fakty: ${item.legal_factual_review_recorded_outcome}`
      : "",
    item.human_review_recorded_outcome ? `człowiek: ${item.human_review_recorded_outcome}` : "",
    item.draft_readiness_review_notes ? `notatka: ${item.draft_readiness_review_notes}` : ""
  ].filter((value) => value.trim().length > 0);
}

function contentDraftReadinessContractValues(
  contract: WordPressDraftPayloadPreviewItem["draft_readiness_review_contract"]
): string[] {
  if (!contract) return [];
  return [
    contract.contract_version ? `contract: ${contract.contract_version}` : "",
    contract.scope ? `zakres: ${contract.scope}` : "",
    ...(contract.allowed_outcomes ?? []).slice(0, 3).map((value) => `outcome: ${value}`),
    ...(contract.required_fields ?? []).slice(0, 4).map((value) => `wymaga: ${value}`),
    ...(contract.blocked_outputs ?? []).slice(0, 4).map((value) => `blokuje: ${value}`)
  ].filter((value) => value.trim().length > 0);
}

function contentStagingHandoffValues(item: WordPressDraftPayloadPreviewItem): string[] {
  return [
    item.staging_handoff_status
      ? `status: ${contentStagingHandoffStatusLabel(item.staging_handoff_status)}`
      : "",
    ...(item.staging_handoff_blockers ?? []).slice(0, 5).map((value) => `blokada: ${value}`)
  ].filter((value) => value.trim().length > 0);
}

function contentStagingHandoffContractValues(
  contract: WordPressDraftPayloadPreviewItem["staging_handoff_contract"]
): string[] {
  if (!contract) return [];
  return [
    contract.contract_version ? `contract: ${contract.contract_version}` : "",
    contract.scope ? `zakres: ${contract.scope}` : "",
    contract.required_next_action_contract ? `następny kontrakt: ${contract.required_next_action_contract}` : "",
    ...(contract.requires_passed_gates ?? []).slice(0, 4).map((value) => `gate: ${value}`),
    ...(contract.blocked_outputs ?? []).slice(0, 4).map((value) => `blokuje: ${value}`)
  ].filter((value) => value.trim().length > 0);
}

function contentPostPublicationMeasurementValues(
  plan: WordPressDraftPayloadPreviewItem["post_publication_measurement_plan"]
): string[] {
  if (!plan) return [];
  return [
    plan.contract_version ? `contract: ${plan.contract_version}` : "",
    plan.status ? `status: ${contentPostPublicationMeasurementStatusLabel(plan.status)}` : "",
    plan.baseline_window ? `baseline: ${plan.baseline_window}` : "",
    ...(plan.followup_windows ?? []).slice(0, 3).map((value) => `follow-up: ${value}`),
    ...(plan.required_source_connectors ?? [])
      .slice(0, 3)
      .map((value) => `źródło: ${value}`),
    ...(plan.blocked_outputs ?? []).slice(0, 3).map((value) => `blokuje: ${value}`)
  ].filter((value) => value.trim().length > 0);
}

function contentPostPublicationMeasurementStatusLabel(value: string): string {
  const labels: Record<string, string> = {
    blocked_until_publish_and_followup_data:
      "zablokowany do publikacji i danych po publikacji"
  };
  return labels[value] ?? value;
}

function contentStagingHandoffStatusLabel(value: string): string {
  const labels: Record<string, string> = {
    blocked_until_draft_gates_pass: "zablokowany do przejścia bramek draftu",
    blocked_until_draft_readiness_review: "zablokowany do review gotowości draftu",
    blocked_until_staging_action_contract: "zablokowany do osobnego kontraktu staging"
  };
  return labels[value] ?? value;
}

function contentDraftOutputKindLabel(value: string): string {
  const labels: Record<string, string> = {
    outline_only_until_gates_pass: "tylko outline do czasu gate review",
    reviewable_polish_draft_preview: "polski draft tylko do review"
  };
  return labels[value] ?? value;
}

function contentGateStatusLabel(value: string) {
  const labels: Record<string, string> = {
    confirmed_current_inventory: "potwierdzone na obecnej stronie",
    confirmed_target_inventory: "potwierdzone na stronie docelowej",
    missing_inventory_match: "brak potwierdzenia inventory",
    current_url_confirmed: "obecny URL potwierdzony",
    needs_target_canonical_review: "sprawdź canonical na nowej stronie",
    blocked_until_mapping_review: "blokada do mapowania URL",
    blocked_until_inventory_review: "blokada do kontroli inventory",
    refresh_or_merge_required: "refresh/merge zamiast nowego artykułu",
    manual_merge_or_create_review: "ręcznie wybierz merge/create",
    create_blocked_until_duplicate_check: "create zablokowane do kontroli",
    not_applicable: "nie dotyczy"
  };
  return labels[value] ?? value;
}

function contentBriefMetricValue(metricName: string, value: string | number | boolean | null) {
  return formatContentMetricValue(metricName, value);
}

function formatNumber(value: number, fractionDigits: number) {
  return value.toLocaleString("pl-PL", {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: 0
  });
}

function contentDecisionTypeLabel(decisionType: ContentDecisionItem["decision_type"]) {
  if (decisionType === "block_until_vendor_read") return "blokada do czasu odczytu";
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
