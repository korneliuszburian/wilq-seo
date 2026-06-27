import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useState } from "react";

import {
  ActionObject,
  Evidence,
  getAction,
  getEvidenceById,
  getOpportunities,
  Opportunity
} from "../lib/api";
import { LoadingBand } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import {
  ActionHumanReviewControls,
  ActionPreviewControls,
  ActionReviewGatePanel,
  ActionValidationControls
} from "./ActionObjectPanels";
import { contentWordPressPostStatusLabel } from "../lib/contentLabels";
import { adsMissingReadContractLabel, marketerBlockedClaimLabels } from "./marketingLabels";

export function ActionDetailSurface({ actionId }: { actionId: string }) {
  const action = useQuery({
    queryKey: ["actions", actionId],
    queryFn: () => getAction(actionId)
  });

  if (action.isLoading) return <LoadingBand />;
  if (action.error) return <ErrorState />;

  if (action.data) return <ActionDetail action={action.data} />;
  return <ErrorState />;
}

export function OpportunityDetailSurface({ opportunityId }: { opportunityId: string }) {
  const opportunities = useQuery({ queryKey: ["opportunities"], queryFn: getOpportunities });

  if (opportunities.isLoading) return <LoadingBand />;
  if (opportunities.error) return <ErrorState />;

  const opportunity = (opportunities.data ?? []).find((item) => item.id === opportunityId);
  if (opportunity) return <OpportunityDetail opportunity={opportunity} />;
  return <ErrorState />;
}

function ActionDetail({ action }: { action: ActionObject }) {
  const visibleAuditEvents = action.audit_events.slice(0, 6);
  const hiddenAuditEventCount = Math.max(0, action.audit_events.length - visibleAuditEvents.length);

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="text-2xl font-semibold tracking-normal">{action.title}</h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={action.status_label} />
        <StatusBadge value={action.validation_status_label} />
        <StatusBadge value={action.risk_label} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Dowody i diagnoza" />
        <p className="text-sm leading-6 text-slate-700">{action.human_diagnosis}</p>
        <div className="mt-4 text-xs text-slate-600">
          Dowody: {action.evidence_summary_label}
        </div>
        <ActionReviewGatePanel action={action} />
        <ActionHumanReviewControls action={action} />
        <ActionPreviewControls action={action} />
        <ActionValidationControls action={action} />
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podgląd zmian" />
        <ActionPayloadPreviewSummary action={action} />
        <TechnicalDetailsPanel
          openLabel="Pokaż dane techniczne akcji"
          closeLabel="Ukryj dane techniczne akcji"
        >
          <pre className="mt-3 max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
            {JSON.stringify(action.payload, null, 2)}
          </pre>
        </TechnicalDetailsPanel>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Historia audytu" />
        {action.audit_events.length === 0 ? (
          <p className="text-sm text-slate-600">Brak zapisanych zdarzeń audytu.</p>
        ) : (
          <div className="grid gap-3">
            {hiddenAuditEventCount > 0 ? (
              <p className="text-xs text-slate-500">
                Pokazano 6 najnowszych z {action.audit_events.length} zdarzeń audytu.
              </p>
            ) : null}
            {visibleAuditEvents.map((event) => (
              <div key={event.id} className="rounded-md border border-line p-3 text-sm">
                <div className="font-medium">{event.event_type_label}</div>
                <div className="mt-1 text-slate-600">
                  {event.summary}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function ActionPayloadPreviewSummary({ action }: { action: ActionObject }) {
  const previewItems = actionPayloadPreviewItems(action.payload);
  if (previewItems.length === 0) {
    return null;
  }
  return (
    <div className="mb-4 grid gap-3">
      {visiblePayloadPreviewItems(previewItems).map((previewItem, index) => (
        <PayloadPreviewCard
          key={payloadPreviewKey(previewItem.item, index)}
          previewItem={previewItem}
        />
      ))}
    </div>
  );
}

type PayloadPreviewItem = {
  kind:
    | "generic"
    | "budget"
    | "recommendation"
    | "customSegment"
    | "negativeKeyword"
    | "searchTermNgram"
    | "demandGenReadiness"
    | "ga4TrackingQuality"
    | "localVisibility"
    | "socialDraftInput"
    | "keywordPlannerAccess"
    | "adsBusinessGuardrail"
    | "contentBrief"
    | "wordpressDraft"
    | "wordpressDraftHandoff";
  item: Record<string, unknown>;
};

function actionPayloadPreviewItems(payload: Record<string, unknown>): PayloadPreviewItem[] {
  const genericItems = Array.isArray(payload.payload_preview)
    ? payload.payload_preview.filter(isRecord).map((item) => ({
        kind: payloadPreviewItemKind(item),
        item
      }))
    : [];
  const budgetItems = Array.isArray(payload.budget_payload_preview)
    ? payload.budget_payload_preview
        .filter(isRecord)
        .map((item) => ({ kind: "budget" as const, item }))
    : [];
  const ngramItems = Array.isArray(payload.ngram_preview)
    ? payload.ngram_preview
        .filter(isRecord)
        .map((item) => ({ kind: "searchTermNgram" as const, item }))
    : [];
  const contentBriefItems = Array.isArray(payload.content_brief_preview)
    ? payload.content_brief_preview
        .filter(isRecord)
        .map((item) => ({ kind: "contentBrief" as const, item }))
    : [];
  const wordpressDraftItems = Array.isArray(payload.wordpress_draft_payload_preview)
    ? payload.wordpress_draft_payload_preview
        .filter(isRecord)
        .map((item) => ({ kind: "wordpressDraft" as const, item }))
    : [];
  const socialDraftItems = Array.isArray(payload.source_inputs)
    ? payload.source_inputs.filter(isRecord).map((item) => ({
        kind: "socialDraftInput" as const,
        item: {
          ...item,
          apply_allowed: false,
          api_mutation_ready: false,
          blocked_claims: payload.blocked_claims,
          connector: payload.connector,
          draft_constraints: payload.draft_constraints,
          draft_constraint_labels: payload.draft_constraint_labels
        }
      }))
    : [];
  const keywordPlannerAccessItems =
    payload.action_type === "configure_google_ads_keyword_planner_access"
      ? [{ kind: "keywordPlannerAccess" as const, item: payload }]
      : [];
  const adsBusinessGuardrailItems =
    payload.action_type === "confirm_ads_target_guardrails" ||
    payload.action_type === "record_ads_strategy_review"
      ? [{ kind: "adsBusinessGuardrail" as const, item: payload }]
      : [];
  return [
    ...genericItems,
    ...budgetItems,
    ...ngramItems,
    ...socialDraftItems,
    ...keywordPlannerAccessItems,
    ...adsBusinessGuardrailItems,
    ...contentBriefItems,
    ...wordpressDraftItems
  ];
}

function PayloadPreviewCard({ previewItem }: { previewItem: PayloadPreviewItem }) {
  if (previewItem.kind === "budget") {
    return <BudgetPayloadPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "recommendation") {
    return <RecommendationPayloadPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "customSegment") {
    return <CustomSegmentPayloadPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "negativeKeyword") {
    return <NegativeKeywordPayloadPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "searchTermNgram") {
    return <SearchTermNgramPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "demandGenReadiness") {
    return <DemandGenReadinessPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "ga4TrackingQuality") {
    return <Ga4TrackingQualityPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "localVisibility") {
    return <LocalVisibilityPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "socialDraftInput") {
    return <SocialDraftInputPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "keywordPlannerAccess") {
    return <KeywordPlannerAccessPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "adsBusinessGuardrail") {
    return <AdsBusinessGuardrailPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "contentBrief") {
    return <ContentBriefPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "wordpressDraft") {
    return <WordPressDraftPreviewCard item={previewItem.item} />;
  }
  if (previewItem.kind === "wordpressDraftHandoff") {
    return <WordPressDraftHandoffPreviewCard item={previewItem.item} />;
  }
  return <GenericPayloadPreviewCard item={previewItem.item} />;
}

function GenericPayloadPreviewCard({ item }: { item: Record<string, unknown> }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Podgląd do sprawdzenia</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {previewIssueLabel(item)}
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <ExecutionStateLine item={item} />
        <PreviewValues label="Przykładowe produkty" values={asStringArray(item.sample_product_ids)} />
        <PreviewValues label="Tytuły próbek" values={asStringArray(item.sample_titles)} />
      </div>
    </article>
  );
}

function WordPressDraftHandoffPreviewCard({ item }: { item: Record<string, unknown> }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Szkic WordPress do sprawdzenia</h3>
          <p className="mt-1 break-words text-xs text-slate-500">
            {stringValue(item.final_canonical_url, stringValue(item.source_public_url, "brak URL"))}
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Wpis do sprawdzenia: {stringValue(item.candidate_id, "brak")}</div>
        <div>Temat: {stringValue(item.topic, "brak")}</div>
        <div>Źródło: {stringValue(item.source_public_url, "brak")}</div>
        <div>Kanoniczny: {stringValue(item.final_canonical_url, "brak")}</div>
        <div>Podgląd: {stringValue(item.preview_url, "brak")}</div>
        <div>Kontrola URL-a kanonicznego: {stringValue(item.canonical_gate_status_label, "brak")}</div>
        <div>Duplikaty: {stringValue(item.duplicate_gate_status_label, "brak")}</div>
        <PreviewValues label="Przekazanie" values={asStringArray(item.wordpress_draft_handoff_summary)} />
        <PreviewValues
          label="Pomiar po publikacji"
          values={asStringArray(item.post_publication_measurement_summary)}
        />
        <div>Następny krok: {stringValue(item.required_next_action_label, "brak")}</div>
        <PreviewValues label="Warunki sprawdzenia" values={asStringArray(item.required_validation_labels)} />
        <PreviewValues label="Czego nie wolno twierdzić" values={asStringArray(item.blocked_claim_labels)} />
        <ExecutionStateLine item={item} />
      </div>
    </article>
  );
}

function NegativeKeywordPayloadPreviewCard({ item }: { item: Record<string, unknown> }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Wykluczenie słowa do sprawdzenia</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {stringValue(item.match_type, "typ dopasowania")}
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Hasło: {stringValue(item.search_term, "brak")}</div>
        <div>Wykluczenie: {stringValue(item.negative_keyword_text, "brak")}</div>
        <div>Dopasowanie: {stringValue(item.match_type, "brak")}</div>
        <div>Poziom: {stringValue(item.level, "brak")}</div>
        <div>Kampania: {stringValue(item.campaign_name, stringValue(item.campaign_id, "brak"))}</div>
        <div>
          Grupa reklam: {stringValue(item.ad_group_name, stringValue(item.ad_group_id, "brak"))}
        </div>
        <PreviewValues
          label="Warunki sprawdzenia"
          values={operatorRequirementValues(item.required_validation, item.required_validation_labels)}
        />
        <div>Czego nie wolno twierdzić: {blockedClaimValues(item.blocked_claims).slice(0, 4).join(", ") || "brak"}</div>
        <ExecutionStateLine item={item} />
      </div>
    </article>
  );
}

function SearchTermNgramPreviewCard({ item }: { item: Record<string, unknown> }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Temat zapytań do sprawdzenia</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            Ocena intencji zapytań bez zapisu zmian
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Temat: {stringValue(item.ngram, "brak")}</div>
        <div>Rozmiar: {formatNumber(item.ngram_size)}</div>
        <div>Zapytania użytkowników: {formatNumber(item.source_search_term_count)}</div>
        <PreviewValues label="Przykłady" values={asStringArray(item.sample_search_terms)} />
        <div>Kliknięcia: {formatNumber(item.clicks)}</div>
        <div>Wyświetlenia: {formatNumber(item.impressions)}</div>
        <div>Koszt: {formatMicrosAsPln(item.cost_micros)}</div>
        <div>Konwersje: {formatNumber(item.conversions)}</div>
        <PreviewValues
          label="Braki"
          values={missingContractValues(item.missing_read_contracts, item.missing_read_contract_labels)}
        />
        <PreviewValues
          label="Warunki sprawdzenia"
          values={operatorRequirementValues(item.required_validation, item.required_validation_labels)}
        />
        <div>Czego nie wolno twierdzić: {blockedClaimValues(item.blocked_claims).slice(0, 4).join(", ") || "brak"}</div>
        <ExecutionStateLine item={item} />
      </div>
    </article>
  );
}

function CustomSegmentPayloadPreviewCard({ item }: { item: Record<string, unknown> }) {
  const safetyReview = isRecord(item.safety_review) ? item.safety_review : {};
  const targetingPreview = Array.isArray(item.targeting_preview)
    ? item.targeting_preview.find(isRecord)
    : undefined;
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Segment odbiorców do sprawdzenia</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {stringValue(item.member_type_label, "wymaga etykiety typu odbiorców z WILQ")}
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Nazwa: {stringValue(item.custom_segment_name, "brak")}</div>
        <div>Typ odbiorców: {stringValue(item.member_type_label, "wymaga etykiety typu odbiorców z WILQ")}</div>
        <PreviewValues label="Hasła źródłowe" values={asStringArray(item.source_terms)} />
        <div>
          Kampania do sprawdzenia:{" "}
          {targetingPreview
            ? stringValue(targetingPreview.campaign_name, stringValue(targetingPreview.campaign_id, "brak"))
            : "brak"}
        </div>
        <div>Bezpieczeństwo: {stringValue(safetyReview.status_label, "wymaga etykiety bezpieczeństwa z WILQ")}</div>
        <PreviewValues
          label="Braki"
          values={missingContractValues(
            safetyReview.missing_requirements,
            safetyReview.missing_requirement_labels
          )}
        />
        <PreviewValues
          label="Warunki sprawdzenia"
          values={operatorRequirementValues(item.required_validation, item.required_validation_labels)}
        />
        <div>Czego nie wolno twierdzić: {blockedClaimValues(item.blocked_claims).slice(0, 4).join(", ") || "brak"}</div>
        <ExecutionStateLine item={item} />
      </div>
    </article>
  );
}

function RecommendationPayloadPreviewCard({ item }: { item: Record<string, unknown> }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Rekomendacja Google Ads do sprawdzenia</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            Ocena rekomendacji bez zapisu zmian
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Typ: {stringValue(item.recommendation_type, "brak")}</div>
        <div>Kampania: {stringValue(item.campaign_id, "brak")}</div>
        <div>Budżet kampanii: {stringValue(item.campaign_budget_id, "brak")}</div>
        <PreviewValues
          label="Warunki sprawdzenia"
          values={operatorRequirementValues(item.required_validation, item.required_validation_labels)}
        />
        <div>Czego nie wolno twierdzić: {blockedClaimValues(item.blocked_claims).slice(0, 4).join(", ") || "brak"}</div>
        <ExecutionStateLine item={item} />
      </div>
    </article>
  );
}

function BudgetPayloadPreviewCard({ item }: { item: Record<string, unknown> }) {
  const safetyReview = isRecord(item.safety_review) ? item.safety_review : {};
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Budżet kampanii do sprawdzenia</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            Ocena budżetu bez zapisu zmian
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Kampania: {stringValue(item.campaign_name, stringValue(item.campaign_id, "brak"))}</div>
        <div>Obecny budżet: {formatMicrosAsPln(item.current_budget_amount_micros)}</div>
        <div>Propozycja: {formatMicrosAsPln(item.proposed_budget_amount_micros)}</div>
        <div>Bezpieczeństwo: {stringValue(safetyReview.status_label, "wymaga etykiety bezpieczeństwa z WILQ")}</div>
        <ExecutionStateLine item={item} />
      </div>
    </article>
  );
}

function DemandGenReadinessPreviewCard({ item }: { item: Record<string, unknown> }) {
  const channelCounts = isRecord(item.campaign_channel_counts) ? item.campaign_channel_counts : {};
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Gotowość Demand Gen do sprawdzenia</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            Ocena gotowości bez zapisu zmian
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Kampanie ocenione: {formatNumber(item.campaign_rows_evaluated)}</div>
        <div>Kanały: {formatChannelCounts(channelCounts)}</div>
        <div>Kampanie Demand Gen: {formatNumber(item.demand_gen_campaign_row_count)}</div>
        <div>Grupy reklam Demand Gen: {formatNumber(item.demand_gen_ad_group_ad_row_count)}</div>
        <div>Kreacje/assets: {formatNumber(item.demand_gen_creative_asset_row_count)}</div>
        <div>Wiersze jakości stron wejścia: {formatNumber(item.demand_gen_landing_quality_row_count)}</div>
        <PreviewValues
          label="Braki"
          values={missingContractValues(item.missing_read_contracts, item.missing_read_contract_labels)}
        />
        <PreviewValues
          label="Warunki sprawdzenia"
          values={operatorRequirementValues(item.required_validation, item.required_validation_labels)}
        />
        <div>Czego nie wolno twierdzić: {blockedClaimValues(item.blocked_claims).slice(0, 4).join(", ") || "brak"}</div>
        <ExecutionStateLine item={item} />
      </div>
    </article>
  );
}

function Ga4TrackingQualityPreviewCard({ item }: { item: Record<string, unknown> }) {
  const metricSnapshot = isRecord(item.metric_snapshot) ? item.metric_snapshot : {};
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Jakość pomiaru GA4 do sprawdzenia</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            Ocena pomiaru bez zapisu zmian
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Strona wejścia: {stringValue(item.landing_page, "brak")}</div>
        <div>Źródło: {stringValue(item.source_medium, "brak")}</div>
        <div>Kampania: {stringValue(item.campaign_name, "brak")}</div>
        <div>Aktywni użytkownicy: {formatNumber(metricSnapshot.active_users)}</div>
        <div>Sesje: {formatNumber(metricSnapshot.sessions)}</div>
        <div>Współczynnik zaangażowania: {formatPercent(metricSnapshot.engagement_rate)}</div>
        <div>Zdarzenia: {formatNumber(metricSnapshot.event_count)}</div>
        <div>Wyświetlenia stron: {formatNumber(metricSnapshot.screen_page_views)}</div>
        <PreviewValues label="Braki wymiarów" values={asStringArray(item.tracking_dimension_gaps)} />
        <PreviewValues
          label="Warunki sprawdzenia"
          values={operatorRequirementValues(item.required_validation, item.required_validation_labels)}
        />
        <div>Czego nie wolno twierdzić: {blockedClaimValues(item.blocked_claims).slice(0, 4).join(", ") || "brak"}</div>
        <ExecutionStateLine item={item} />
      </div>
    </article>
  );
}

function LocalVisibilityPreviewCard({ item }: { item: Record<string, unknown> }) {
  const metricSnapshot = isRecord(item.metric_snapshot) ? item.metric_snapshot : {};
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Widoczność lokalna do sprawdzenia</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            Ocena lokalna bez zapisu zmian
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Widoczność: {formatNumber(metricSnapshot.localo_avg_visibility_current)}</div>
        <div>Zmiana widoczności: {formatPercent(metricSnapshot.localo_avg_visibility_change)}</div>
        <div>Średnia pozycja grid: {formatNumber(metricSnapshot.localo_avg_latest_grid_position)}</div>
        <div>Monitorowane frazy: {formatNumber(metricSnapshot.localo_tracked_keyword_count)}</div>
        <div>Aktywne miejsca: {formatNumber(metricSnapshot.localo_active_place_count)}</div>
        <div>Ocena: {formatNumber(metricSnapshot.localo_avg_rating)}</div>
        <div>Opinie: {formatNumber(metricSnapshot.localo_reviews_count)}</div>
        <div>Odsetek odpowiedzi na opinie: {formatPercent(metricSnapshot.localo_review_reply_rate)}</div>
        <PreviewValues label="Dozwolone odczyty" values={readContractValues(item.allowed_contracts)} />
        <PreviewValues
          label="Braki"
          values={missingContractValues(item.missing_read_contracts, item.missing_read_contract_labels)}
        />
        <PreviewValues
          label="Warunki sprawdzenia"
          values={operatorRequirementValues(item.required_validation, item.required_validation_labels)}
        />
        <div>Czego nie wolno twierdzić: {blockedClaimValues(item.blocked_claims).slice(0, 4).join(", ") || "brak"}</div>
        <ExecutionStateLine item={item} />
      </div>
    </article>
  );
}

function SocialDraftInputPreviewCard({ item }: { item: Record<string, unknown> }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Materiały do posta social</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {stringValue(item.connector, "social")}
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Źródło: {stringValue(item.source_connector, "brak")}</div>
        <div>Metryka: {stringValue(item.metric_name, "brak")}</div>
        <div>Wartość: {formatMetricValue(item.value)}</div>
        <div>Kontekst: {stringValue(item.context_summary, "sygnał źródłowy WILQ")}</div>
        <PreviewValues
          label="Ograniczenia"
          values={operatorRequirementValues(item.draft_constraints, item.draft_constraint_labels)}
        />
        <div>Czego nie wolno twierdzić: {blockedClaimValues(item.blocked_claims).slice(0, 4).join(", ") || "brak"}</div>
        <PublicationStateLine item={item} />
      </div>
    </article>
  );
}

function KeywordPlannerAccessPreviewCard({ item }: { item: Record<string, unknown> }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">
            Dostęp do Keyword Plannera do odblokowania
          </h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            Blokada dostępu do odblokowania
          </p>
        </div>
        <StatusBadge value="blocked" />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Zablokowany dostęp: {stringValue(item.blocked_api, "brak")}</div>
        <div>Powód: {stringValue(item.blocked_reason, "brak")}</div>
        <PreviewValues
          label="Wymagany stan"
          values={missingContractValues(item.required_google_ads_state, item.required_google_ads_state_labels)}
        />
        <PreviewValues label="Kroki" values={asStringArray(item.helper_steps)} />
        <PreviewValues
          label="Warunki sprawdzenia"
          values={operatorRequirementValues(item.required_validation, item.required_validation_labels)}
        />
        <div>Czego nie wolno twierdzić: {blockedClaimValues(item.blocked_claims).slice(0, 4).join(", ") || "brak"}</div>
        <ExecutionStateLine item={item} />
      </div>
    </article>
  );
}

function AdsBusinessGuardrailPreviewCard({ item }: { item: Record<string, unknown> }) {
  const context = isRecord(item.current_context) ? item.current_context : {};
  const targetEnvOptions = isRecord(item.target_env_options) ? item.target_env_options : {};
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Zasady bezpieczeństwa Ads do sprawdzenia</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            Ocena celu biznesowego bez zapisu zmian
          </p>
        </div>
        <StatusBadge value="blocked" />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Marża: {formatPercent(context.profit_margin)}</div>
        <div>Cel biznesowy: {stringValue(context.business_goal, "brak")}</div>
        <div>Cel budżetu: {stringValue(context.budget_goal, "brak")}</div>
        <div>Docelowy zwrot z reklam: {formatMetricValue(context.target_roas)}</div>
        <div>Docelowy koszt pozyskania celu: {formatMicrosAsPln(context.target_cpa_micros)}</div>
        <PreviewValues label="Źródła konfiguracji" values={asStringArray(context.configured_sources)} />
        <PreviewValues
          label="Braki"
          values={missingContractValues(item.missing_read_contracts, item.missing_read_contract_labels)}
        />
        <PreviewValues
          label="Opcje celu"
          values={targetOptionValues(targetEnvOptions.target_roas_or_cpa)}
        />
        <PreviewValues
          label="Po potwierdzeniu"
          values={operatorRequirementValues(
            item.allowed_uses_after_confirmation,
            item.allowed_uses_after_confirmation_labels
          )}
        />
        <PreviewValues
          label="Warunki przeglądu"
          values={operatorRequirementValues(item.operator_review_gates, item.operator_review_gate_labels)}
        />
        <div>Ostatni przegląd strategii: {strategyReviewSummary(item.latest_strategy_review)}</div>
        <PreviewValues
          label="Warunki sprawdzenia"
          values={operatorRequirementValues(item.required_validation, item.required_validation_labels)}
        />
        <div>Czego nie wolno twierdzić: {blockedClaimValues(item.blocked_claims).slice(0, 4).join(", ") || "brak"}</div>
        <ExecutionStateLine item={item} />
      </div>
    </article>
  );
}

function ContentBriefPreviewCard({ item }: { item: Record<string, unknown> }) {
  const metricSnapshot = isRecord(item.metric_snapshot) ? item.metric_snapshot : {};
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Plan treści do sprawdzenia</h3>
          <p className="mt-1 break-words text-xs text-slate-500">
            {contentPrimaryUrlValue(item)}
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Temat: {stringValue(item.topic, "brak")}</div>
        <div>Tryb: {stringValue(item.mode_label, "wymaga etykiety trybu z WILQ")}</div>
        <div>WordPress: {stringValue(item.wordpress_inventory_match, "brak")}</div>
        <div>Opcje: {asStringArray(item.decision_option_labels).join(", ") || "brak"}</div>
        <div>Cel planu treści: {stringValue(item.brief_goal, "brak")}</div>
        <div>Intencja: {stringValue(item.intent, "brak")}</div>
        <div>Kąt treści: {stringValue(item.content_angle, "brak")}</div>
        <div>Odbiorca: {stringValue(item.audience, "brak")}</div>
        <div>H1: {stringValue(item.h1_direction, "brak")}</div>
        <div>H2: {asStringArray(item.h2_direction).slice(0, 4).join(", ") || "brak"}</div>
        <div>FAQ: {asStringArray(item.faq_direction).slice(0, 4).join(", ") || "brak"}</div>
        <div>CTA: {stringValue(item.cta_direction, "brak")}</div>
        <div>Adresy: {contentUrlSemanticsValue(item)}</div>
        <div>Obiekcje: {asStringArray(item.key_objections).slice(0, 3).join(", ") || "brak"}</div>
        <div>Źródła faktów: {asStringArray(item.source_facts).slice(0, 3).join(", ") || "brak"}</div>
        <div>Brakujące dowody: {asStringArray(item.missing_evidence).slice(0, 3).join(", ") || "brak"}</div>
        <div>
          Kliknięcia: {formatNumber(metricSnapshot.clicks)}; Wyświetlenia:{" "}
          {formatNumber(metricSnapshot.impressions)}
        </div>
        <div>
          CTR: {formatPercent(metricSnapshot.ctr)}; Pozycja:{" "}
          {formatNumber(metricSnapshot.average_position)}
        </div>
        <PreviewValues label="Blokady publikacji" values={asStringArray(item.publication_blocker_labels)} />
        <PreviewValues label="Warunki sprawdzenia" values={asStringArray(item.required_validation_labels)} />
        <div>
          Publikacja: {item.api_mutation_ready === true ? "gotowa" : "zablokowana"}; zapis zmian:{" "}
          {item.apply_allowed === true ? "dopuszczony" : "zablokowany"}
        </div>
      </div>
    </article>
  );
}

function contentPrimaryUrlValue(item: Record<string, unknown>) {
  return stringValue(
    item.final_canonical_url,
    stringValue(
      item.intended_final_url,
      stringValue(item.source_public_url, stringValue(item.preview_url, "brak URL"))
    )
  );
}

function WordPressDraftPreviewCard({ item }: { item: Record<string, unknown> }) {
  const draftPayload = isRecord(item.draft_payload) ? item.draft_payload : {};
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">Szkic WordPress do sprawdzenia</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            Szkic bez publikacji
          </p>
        </div>
        <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        <div>Temat: {stringValue(item.topic, "brak")}</div>
        <div>Intencja: {stringValue(item.intent, "brak")}</div>
        <div>
          Status wpisu:{" "}
          {contentWordPressPostStatusLabel(
            stringValue(item.post_status, stringValue(draftPayload.post_status, ""))
          )}
        </div>
        <div>Tytuł szkicu: {stringValue(draftPayload.post_title, "brak")}</div>
        <div>Adresy: {contentUrlSemanticsValue(item)}</div>
        <PreviewValues label="Kontrole treści" values={asStringArray(item.content_gate_status_summary)} />
        <PreviewValues label="Co blokuje szkic" values={asStringArray(item.draft_blocker_labels)} />
        <PreviewValues label="Warunki szkicu" values={asStringArray(item.draft_generation_summary)} />
        <PreviewValues label="Gotowość po sprawdzeniu" values={asStringArray(item.draft_readiness_review_summary)} />
        <PreviewValues
          label="Kontrola szkicu"
          values={asStringArray(item.draft_readiness_review_contract_summary)}
        />
        <PreviewValues label="Szkic WordPress" values={asStringArray(item.wordpress_draft_handoff_summary)} />
        <PreviewValues
          label="Warunki szkicu WordPress"
          values={asStringArray(item.wordpress_draft_handoff_contract_summary)}
        />
        <PreviewValues
          label="Pomiar po publikacji"
          values={asStringArray(item.post_publication_measurement_summary)}
        />
        <PreviewValues label="Warunki sprawdzenia" values={asStringArray(item.required_validation_labels)} />
        <div>
          Zapis zmian: {item.apply_allowed === true ? "dopuszczony" : "zablokowany"}; gotowość systemu:{" "}
          {item.api_mutation_ready === true ? "gotowy" : "zablokowany"}
        </div>
      </div>
    </article>
  );
}

function prioritizePayloadPreviewItems(items: PayloadPreviewItem[]) {
  return [...items].sort((left, right) => {
    if (left.kind !== right.kind) {
      return payloadPreviewKindOrder(left.kind) - payloadPreviewKindOrder(right.kind);
    }
    const leftHasSamples = asStringArray(left.item.sample_product_ids).length > 0;
    const rightHasSamples = asStringArray(right.item.sample_product_ids).length > 0;
    if (leftHasSamples === rightHasSamples) return 0;
    return leftHasSamples ? -1 : 1;
  });
}

function visiblePayloadPreviewItems(items: PayloadPreviewItem[]) {
  const sortedItems = prioritizePayloadPreviewItems(items);
  const visibleItems = sortedItems.slice(0, 4);
  const draftItem = sortedItems.find((item) => item.kind === "wordpressDraft");
  if (draftItem && !visibleItems.some((item) => item.kind === "wordpressDraft")) {
    visibleItems.splice(Math.max(visibleItems.length - 1, 0), 1, draftItem);
  }
  return visibleItems;
}

function payloadPreviewKindOrder(kind: PayloadPreviewItem["kind"]) {
  if (kind === "budget") return 0;
  if (kind === "recommendation") return 1;
  if (kind === "customSegment") return 2;
  if (kind === "negativeKeyword") return 3;
  if (kind === "searchTermNgram") return 4;
  if (kind === "demandGenReadiness") return 5;
  if (kind === "ga4TrackingQuality") return 6;
  if (kind === "localVisibility") return 7;
  if (kind === "socialDraftInput") return 8;
  if (kind === "keywordPlannerAccess") return 9;
  if (kind === "adsBusinessGuardrail") return 10;
  if (kind === "contentBrief") return 11;
  if (kind === "wordpressDraft") return 12;
  if (kind === "wordpressDraftHandoff") return 13;
  return 13;
}

function payloadPreviewItemKind(item: Record<string, unknown>): PayloadPreviewItem["kind"] {
  if (
    typeof item.negative_keyword_text === "string" ||
    (typeof item.search_term === "string" && typeof item.match_type === "string")
  ) {
    return "negativeKeyword";
  }
  if (
    typeof item.custom_segment_name === "string" ||
    (typeof item.member_type === "string" && Array.isArray(item.source_terms))
  ) {
    return "customSegment";
  }
  if (
    stringValue(item.operation_type, "") === "ApplyRecommendationOperation" ||
    typeof item.recommendation_type === "string"
  ) {
    return "recommendation";
  }
  if (
    stringValue(item.operation_type, "") === "DemandGenReadinessReview" ||
    stringValue(item.preview_contract, "") === "demand_gen_readiness_review_preview_v1"
  ) {
    return "demandGenReadiness";
  }
  if (
    stringValue(item.operation_type, "") === "tracking_quality_review" ||
    stringValue(item.preview_contract, "") === "ga4_tracking_quality_review_v1"
  ) {
    return "ga4TrackingQuality";
  }
  if (
    stringValue(item.operation_type, "") === "local_visibility_review" ||
    stringValue(item.preview_contract, "") === "local_visibility_review_preview_v1"
  ) {
    return "localVisibility";
  }
  if (
    stringValue(item.operation_type, "") === "wordpress_draft_handoff_review" ||
    stringValue(item.preview_contract, "") === "wordpress_draft_handoff_preview_v1"
  ) {
    return "wordpressDraftHandoff";
  }
  return "generic";
}

function PreviewValues({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) {
    return (
      <div>
        {label}: <span className="text-slate-500">brak</span>
      </div>
    );
  }
  return (
    <div>
      {label}: {values.slice(0, 4).join(", ")}
      {values.length > 4 ? ` +${values.length - 4}` : ""}
    </div>
  );
}

function operatorRequirementValues(value: unknown, labelValue?: unknown) {
  const labelValues = asStringArray(labelValue);
  if (labelValues.length > 0) {
    return labelValues.filter((item, index, values) => values.indexOf(item) === index);
  }
  return asStringArray(value).filter((item) => !looksLikeTechnicalKey(item));
}

function missingContractValues(value: unknown, labelValue?: unknown) {
  const labelValues = asStringArray(labelValue);
  if (labelValues.length > 0) {
    return labelValues.filter((item, index, values) => values.indexOf(item) === index);
  }
  return asStringArray(value).filter((item) => !looksLikeTechnicalKey(item));
}

function looksLikeTechnicalKey(value: string) {
  return /^[a-z0-9]+(?:_[a-z0-9]+)+$/.test(value);
}

function readContractValues(value: unknown) {
  const labels: Record<string, string> = {
    local_rankings: "lokalne pozycje",
    reviews: "opinie",
    gbp_visibility: "widoczność Google Business Profile",
    competitor_visibility: "widoczność konkurencji"
  };
  return asStringArray(value)
    .map((item) => {
      const label = labels[item] ?? adsMissingReadContractLabel(item);
      return label !== item ? label : "odczyt techniczny";
    })
    .filter((item, index, values) => values.indexOf(item) === index);
}

function targetOptionValues(value: unknown) {
  const labels: Record<string, string> = {
    WILQ_ADS_TARGET_ROAS: "docelowy zwrot z reklam",
    WILQ_ADS_TARGET_CPA_MICROS: "docelowy koszt pozyskania celu"
  };
  return asStringArray(value).map((item) => labels[item] ?? "opcja celu do ustawienia");
}

function technicalDetailCount(value: Record<string, unknown>) {
  const count = Object.values(value).filter(
    (dimensionValue) =>
      typeof dimensionValue === "string" ||
      typeof dimensionValue === "number" ||
      typeof dimensionValue === "boolean"
  ).length;
  if (count === 0) return "brak";
  if (count === 1) return "1 pole techniczne";
  return `${count} pola techniczne`;
}

function ExecutionStateLine({ item }: { item: Record<string, unknown> }) {
  return (
    <div>
      Zapis zmian: {item.apply_allowed === true ? "dopuszczony" : "zablokowany"}; gotowość systemu:{" "}
      {item.api_mutation_ready === true ? "gotowy" : "zablokowany"}
    </div>
  );
}

function PublicationStateLine({ item }: { item: Record<string, unknown> }) {
  return (
    <div>
      Publikacja: {item.apply_allowed === true ? "dopuszczona" : "zablokowana"}; gotowość systemu:{" "}
      {item.api_mutation_ready === true ? "gotowy" : "zablokowany"}
    </div>
  );
}

function blockedClaimValues(value: unknown) {
  return marketerBlockedClaimLabels(asStringArray(value));
}

function previewIssueLabel(item: Record<string, unknown>) {
  const issueType =
    typeof item.issue_type_label === "string"
      ? item.issue_type_label
      : "wymaga etykiety problemu z WILQ";
  const attribute =
    typeof item.affected_attribute_label === "string"
      ? item.affected_attribute_label
      : "wymaga etykiety atrybutu z WILQ";
  return `${issueType} / ${attribute}`;
}

function payloadPreviewKey(item: Record<string, unknown>, index: number) {
  return typeof item.id === "string" ? item.id : `payload-preview-${index}`;
}

function strategyReviewSummary(value: unknown) {
  if (!isRecord(value)) {
    return "brak";
  }
  return stringValue(value.outcome, "zapisany");
}

function formatChannelCounts(value: Record<string, unknown>) {
  const entries = Object.entries(value).filter(([, count]) => typeof count === "number");
  if (entries.length === 0) {
    return "brak";
  }
  return entries.map(([channel, count]) => `${channel}=${formatNumber(count)}`).join(", ");
}

function formatMicrosAsPln(value: unknown) {
  if (typeof value !== "number") {
    return "brak";
  }
  const plnValue = value / 1_000_000;
  return `${new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(plnValue)} PLN`;
}

function formatNumber(value: unknown) {
  if (typeof value !== "number") {
    return "brak";
  }
  return new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 3 }).format(value);
}

function formatPercent(value: unknown) {
  if (typeof value !== "number") {
    return "brak";
  }
  return new Intl.NumberFormat("pl-PL", {
    maximumFractionDigits: 2,
    style: "percent"
  }).format(value);
}

function formatMetricValue(value: unknown) {
  if (typeof value === "number") {
    return formatNumber(value);
  }
  if (typeof value === "boolean") {
    return value ? "tak" : "nie";
  }
  if (typeof value === "string" && value.length > 0) {
    return value;
  }
  return "brak";
}

function stringValue(value: unknown, fallback: string) {
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function EvidenceDetailSurface({ evidenceId }: { evidenceId: string }) {
  const evidence = useQuery({
    queryKey: ["evidence", evidenceId],
    queryFn: () => getEvidenceById(evidenceId),
    enabled: evidenceId.length > 0
  });

  if (evidence.isLoading) return <LoadingBand />;
  if (evidence.error || !evidence.data) return <ErrorState />;
  return <EvidenceDetail evidence={evidence.data} />;
}

function EvidenceDetail({ evidence }: { evidence: Evidence }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="break-words text-2xl font-semibold tracking-normal">
        {evidence.title_label}
      </h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={evidence.source_connector_label} />
        <StatusBadge value={evidence.source_type_label} />
        <StatusBadge value={evidence.freshness_label} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podsumowanie dowodu" />
        <p className="text-sm leading-6 text-slate-700">{evidence.summary}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Źródło: {evidence.source_connector_label}</div>
          <div>Typ źródła: {evidence.source_type_label}</div>
          <div>Zebrano: {evidence.collected_at}</div>
          <div>Świeżość: {evidence.freshness_label}</div>
        </div>
        <TechnicalDetailsPanel
          className="mt-4"
          openLabel="Pokaż szczegóły techniczne dowodu"
          closeLabel="Ukryj szczegóły techniczne dowodu"
        >
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <div>ID dowodu: {evidence.id}</div>
            <div>ID źródła: {evidence.source_id}</div>
            <div>Referencja źródłowa: {evidence.raw_ref ?? "brak"}</div>
          </div>
        </TechnicalDetailsPanel>
      </section>
    </main>
  );
}

function OpportunityDetail({ opportunity }: { opportunity: Opportunity }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="text-2xl font-semibold tracking-normal">{opportunity.title}</h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={opportunity.domain_label} />
        <StatusBadge value={opportunity.risk} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Diagnoza" />
        <p className="text-sm leading-6 text-slate-700">{opportunity.human_diagnosis}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Dowody: {opportunity.evidence_summary_label}</div>
          <div>Źródła: {opportunity.source_connector_labels.join(", ")}</div>
        </div>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Metryki z dowodów" />
        {opportunity.metrics.length === 0 ? (
          <p className="text-sm text-slate-600">Brak realnych metryk z dowodami.</p>
        ) : (
          <>
            <MetricTileSummary tiles={opportunity.metric_tiles} />
            <TechnicalDetailsPanel
              className="mt-4"
              openLabel="Pokaż szczegóły techniczne metryk"
              closeLabel="Ukryj szczegóły techniczne metryk"
            >
              <pre className="mt-3 max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
                {JSON.stringify(opportunity.metrics, null, 2)}
              </pre>
            </TechnicalDetailsPanel>
          </>
        )}
      </section>
    </main>
  );
}

function MetricTileSummary({ tiles }: { tiles: Record<string, string | number> }) {
  const entries = Object.entries(tiles).slice(0, 8);
  if (entries.length === 0) {
    return <p className="text-sm text-slate-600">Metryki są dostępne w szczegółach technicznych.</p>;
  }
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {entries.map(([label, value]) => (
        <span
          key={label}
          className="rounded border border-line bg-slate-50 px-2 py-1 text-xs text-slate-700"
        >
          {label}: {value}
        </span>
      ))}
    </div>
  );
}

function TechnicalDetailsPanel({
  openLabel,
  closeLabel,
  className = "",
  children
}: {
  openLabel: string;
  closeLabel: string;
  className?: string;
  children: ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className={`${className} rounded-md border border-line bg-slate-50 p-3 text-xs text-slate-700`}>
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="font-medium text-ink"
      >
        {isOpen ? closeLabel : openLabel}
      </button>
      {isOpen ? children : null}
    </div>
  );
}

function contentUrlSemanticsValue(item: Record<string, unknown>) {
  const sourceUrl = stringValue(item.source_public_url, "");
  const finalUrl = stringValue(
    item.final_canonical_url,
    stringValue(item.intended_final_url, "")
  );
  const previewUrl = stringValue(item.preview_url, "");
  const parts = [
    sourceUrl ? `publiczny: ${sourceUrl}` : "",
    finalUrl ? `kanoniczny: ${finalUrl}` : "",
    previewUrl ? `podgląd: ${previewUrl}` : "",
  ].filter(Boolean);
  return parts.join("; ") || "brak";
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
