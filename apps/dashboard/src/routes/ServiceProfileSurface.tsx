import { useQuery } from "@tanstack/react-query";
import { LockKeyhole, ShieldCheck } from "lucide-react";
import { useState } from "react";

import {
  getContentServiceProfile,
  type ContentServiceProfileResponse
} from "../lib/api";
import {
  BlockerNotice,
  LoadingBand,
  MetricTile,
  PlainChipRow
} from "../components/OperatorPrimitives";
import {
  CoverageGaps,
  PrivateProposalCards,
  ReviewActions
} from "./ServiceProfileSections/ProposalsSection";
import {
  ApprovalReadinessPanel,
  SourceFactCoveragePanel
} from "./ServiceProfileSections/ReadinessSection";
import {
  humanizeEnum,
  priorityLabel,
  reviewScopeLabel,
  type ServiceSection
} from "./ServiceProfileSections/Shared";

const REVIEW_DECISION_LABELS: Record<string, string> = {
  approve: "zatwierdź",
  needs_changes: "wróć z poprawkami",
  stale: "oznacz jako nieaktualne",
  reject: "odrzuć"
};

export function ServiceProfileSurface() {
  const profile = useQuery({
    queryKey: ["content-service-profile"],
    queryFn: getContentServiceProfile
  });

  if (profile.isLoading) return <LoadingBand />;
  if (profile.error || !profile.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać Profilu usług. WILQ nie pokazuje wiedzy bez kontraktu API." />
      </main>
    );
  }

  return <ServiceProfileLoaded data={profile.data} />;
}

function ServiceProfileLoaded({ data }: { data: ContentServiceProfileResponse }) {
  const [showFullReview, setShowFullReview] = useState(false);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Profil usług Ekologus</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Podgląd tego, co WILQ wie o usługach, twierdzeniach i wymaganych
            dowodach. Ten widok nie edytuje kart i nie zatwierdza faktów jako wiedzy produkcyjnej.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          <MetricTile label="Karty" value={data.coverage_summary.card_count} />
          <MetricTile label="Usługi" value={data.coverage_summary.service_card_count} />
          <MetricTile
            label="Do sprawdzenia"
            value={data.coverage_summary.source_backed_review_required_count}
          />
          <MetricTile label="Luki" value={data.coverage_summary.missing_required_area_count} />
        </div>
      </div>

      <ServiceProfileTodayPanel data={data} />
      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Pełny przegląd wiedzy
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Pierwszy ekran pokazuje najbliższy review item. Rozwiń pełny
              przegląd, gdy chcesz zobaczyć gotowość zatwierdzenia, źródła,
              luki, usługi, politykę twierdzeń i prywatne propozycje ekologus-ai.
            </p>
          </div>
          <button
            type="button"
            className="min-h-9 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:border-action hover:text-action"
            onClick={() => setShowFullReview((value) => !value)}
          >
            {showFullReview ? "Ukryj pełny przegląd wiedzy" : "Pokaż pełny przegląd wiedzy"}
          </button>
        </div>
      </section>

      {showFullReview ? <ServiceProfileFullReview data={data} /> : null}
    </main>
  );
}

function ServiceProfileFullReview({ data }: { data: ContentServiceProfileResponse }) {
  return (
    <>
      <ApprovalReadinessPanel readiness={data.approval_readiness} />
      <SourceFactCoveragePanel
        coverage={data.source_fact_coverage}
        privateReviewValue={data.private_review_value}
        List={List}
        formatCounts={formatCounts}
      />

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-normal text-slate-700">
              <ShieldCheck aria-hidden="true" size={16} />
              Gotowość wiedzy
            </div>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              {data.coverage_summary.status_label}. {data.coverage_summary.safe_next_step}
            </p>
          </div>
          <PlainChipRow
            values={[
              data.coverage_summary.ready_for_daily_content
                ? "wiedza produkcyjna gotowa"
                : "wiedza produkcyjna zablokowana",
              data.review_policy.can_request_review ? "review request dostępny" : null,
              data.read_only ? "tylko odczyt" : null
            ]}
          />
        </div>
        <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-wait">
          {data.review_policy.review_required_label}
        </div>
      </section>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex items-start gap-2">
          <LockKeyhole aria-hidden="true" className="mt-0.5 shrink-0 text-slate-500" size={16} />
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Polityka zapisu
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              {data.review_policy.blocked_write_reason}
            </p>
          </div>
        </div>
      </section>

      <CoverageGaps gaps={data.coverage_gaps} />

      <ReviewActions
        actions={data.review_actions}
        summary={data.review_action_summary}
        reviewDecisionLabel={reviewDecisionLabel}
      />

      <section className="mb-6 grid gap-4 lg:grid-cols-2">
        {data.service_sections.map((section) => (
          <ServiceCard key={section.card_id} section={section} />
        ))}
      </section>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
          Twierdzenia i wymagane dowody
        </h2>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {data.claim_policy_sections.slice(0, 4).map((section) => (
            <div key={section.card_id} className="rounded-md border border-line p-3">
              <h3 className="text-sm font-semibold">{section.title}</h3>
              <PlainChipRow
                className="mt-2"
                values={[
                  `${section.claims_needing_review.length} twierdzeń do review`,
                  `${section.forbidden_claims.length} twierdzeń zablokowanych`,
                  `${section.measurement_sensitive_claims.length} pomiarowych`
                ]}
              />
              <p className="mt-2 text-sm leading-6 text-slate-600">{section.safe_next_step}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-md border border-line bg-white p-4">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
          Źródła prywatne
        </h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          {data.private_source_proposal_summary.safe_next_step}
        </p>
        <PlainChipRow
          className="mt-3"
          values={[
            data.private_source_proposal_summary.proposal_protocol_available
              ? "protokół proposal dostępny"
              : "brak protokołu",
            `${data.private_source_proposal_summary.proposal_count} propozycji`,
            `${data.private_source_proposal_summary.service_proposal_count} usługowe`,
            `${data.private_source_proposal_summary.claim_policy_proposal_count} polityki twierdzeń`,
            data.private_source_proposal_summary.evidence_requirement_proposal_count > 0
              ? `${data.private_source_proposal_summary.evidence_requirement_proposal_count} wymagania dowodowe`
              : null,
            `${data.private_source_proposal_summary.review_required_count} do review`,
            `${data.private_source_proposal_summary.approved_count} zatwierdzonych`,
            data.private_source_proposal_summary.promotion_ready
              ? "promocja gotowa"
              : "promocja zablokowana"
          ]}
        />
        <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3">
          <p className="text-sm leading-6 text-wait">
            {data.private_source_proposal_summary.promotion_blocked_reason}
          </p>
          <List
            label="Warunki przed reviewed source fact"
            values={data.private_source_proposal_summary.promotion_checklist}
          />
        </div>
        {data.private_source_proposal_summary.proposal_source_labels.length > 0 ? (
          <ul className="mt-3 space-y-1 text-sm text-slate-600">
            {data.private_source_proposal_summary.proposal_source_labels.map((label) => (
              <li key={label}>{label}</li>
            ))}
          </ul>
        ) : null}
        <PrivateProposalCards proposals={data.private_source_proposals} List={List} />
        <details className="mt-4 text-xs text-slate-500">
          <summary className="cursor-pointer font-semibold text-slate-600">Szczegóły techniczne</summary>
          <div className="mt-2 space-y-1">
            <p>Endpoint kart: {data.technical_trace.knowledge_card_endpoint}</p>
            <p>Source facts: {data.technical_trace.source_fact_count}</p>
            <p>Protokół: {data.technical_trace.private_source_protocol_doc}</p>
          </div>
        </details>
      </section>
    </>
  );
}

function ServiceProfileTodayPanel({ data }: { data: ContentServiceProfileResponse }) {
  const readiness = data.production_depth_readiness;
  const proposals = data.private_source_proposal_summary;
  const review = data.review_action_summary;

  return (
    <section className="mb-6 rounded-md border border-action/30 bg-action/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-action">
            Wiedza Ekologus: co dziś sprawdzić
          </div>
          <h2 className="mt-1 text-lg font-semibold tracking-normal text-ink">
            Są źródła i propozycje, ale produkcyjne treści są nadal zablokowane
          </h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
            {data.coverage_summary.safe_next_step}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          <MetricTile label="Karty" value={data.coverage_summary.card_count} />
          <MetricTile label="Zatwierdzone" value={data.coverage_summary.approved_current_count} />
          <MetricTile label="Do review" value={readiness.source_backed_review_required_count} />
          <MetricTile label="ekologus-ai" value={proposals.proposal_count} />
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Kolejność review</h3>
          <ol className="mt-3 grid gap-2 text-sm leading-6 text-slate-700">
            <li className="grid grid-cols-[1.5rem_1fr] gap-2">
              <span className="font-semibold text-action">1.</span>
              <span>Najpierw publiczne karty usług Ekologus.</span>
            </li>
            <li className="grid grid-cols-[1.5rem_1fr] gap-2">
              <span className="font-semibold text-action">2.</span>
              <span>Potem prywatne propozycje ekologus-ai: usługi, polityki twierdzeń i wymagania dowodowe.</span>
            </li>
            <li className="grid grid-cols-[1.5rem_1fr] gap-2">
              <span className="font-semibold text-action">3.</span>
              <span>Dopiero po reviewerze, freshness i source lineage można myśleć o reviewed source fact.</span>
            </li>
          </ol>
          <p className="mt-3 text-sm font-medium leading-6 text-ink">
            {review.safe_next_step}
          </p>
          {review.first_review_action_label ? (
            <div className="mt-3 rounded-md border border-action/30 bg-action/5 p-3">
              <div className="text-xs font-semibold uppercase tracking-normal text-action">
                Pierwszy review item
              </div>
              <p className="mt-1 text-sm font-semibold leading-6 text-ink">
                {review.first_review_action_label}
              </p>
              {review.first_review_action_reason ? (
                <p className="mt-1 text-sm leading-6 text-slate-700">
                  {review.first_review_action_reason}
                </p>
              ) : null}
              {review.first_review_safe_next_step ? (
                <p className="mt-1 text-sm leading-6 text-slate-700">
                  {review.first_review_safe_next_step}
                </p>
              ) : null}
              <PlainChipRow
                className="mt-2"
                values={[
                  review.first_review_action_scope
                    ? reviewScopeLabel(review.first_review_action_scope)
                    : null,
                  review.first_review_action_priority
                    ? priorityLabel(review.first_review_action_priority)
                    : null,
                  review.first_review_action_target_card_id,
                  review.first_review_action_gap_id
                ]}
              />
              <List
                label="Co trzeba sprawdzić"
                values={reviewRequiredFieldLabels(review.first_review_required_fields)}
              />
            </div>
          ) : null}
        </div>

        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Co blokuje produkcję</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {proposals.promotion_blocked_reason}
          </p>
          <div className="mt-3 grid gap-1 text-xs leading-5 text-slate-600">
            <List label="Blokady" values={readiness.blocker_labels} />
            <List label="Warunki promocji" values={proposals.promotion_checklist.slice(0, 3)} />
          </div>
        </div>
      </div>
    </section>
  );
}

function reviewRequiredFieldLabels(fields: string[]) {
  const labels: Record<string, string> = {
    action_id: "jaka decyzja ma zostać zapisana",
    target_card_id: "której karty wiedzy dotyczy review",
    decision: "czy właściciel zatwierdza, odrzuca albo zostawia do poprawy",
    source_trace_clear: "czy źródła są jasne i wystarczające",
    blocked_claims_reviewed: "czy ryzykowne twierdzenia zostały sprawdzone",
    notes: "krótka notatka z decyzji"
  };
  return fields.map((field) => labels[field] ?? field.replaceAll("_", " "));
}

function ServiceCard({ section }: { section: ServiceSection }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">{section.title}</h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">{section.summary}</p>
        </div>
        <span className="rounded-md border border-line px-2 py-1 text-xs text-slate-600">
          {section.status_label}
        </span>
      </div>
      <PlainChipRow
        className="mt-3"
        values={[
          section.confidence_label,
          section.freshness_label,
          `${section.claims_needing_review.length} review`,
          `${section.forbidden_claims.length} blokad`
        ]}
      />
      <div className="mt-3 grid gap-3 text-sm leading-6 text-slate-600">
        <p>{section.safe_next_step}</p>
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <div className="font-semibold text-slate-700">Źródła i review</div>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {section.review_request_hint}
          </p>
          <PlainChipRow
            className="mt-2"
            values={[
              ...section.source_connector_labels,
              ...section.source_fact_ids.slice(0, 3)
            ]}
          />
          <List label="Dowody WILQ" values={section.evidence_ids.slice(0, 3)} />
          <List label="Ślad źródłowy" values={section.source_lineage_labels.slice(0, 3)} />
        </div>
        <List label="Dopasowanie" values={section.service_fit_terms.slice(0, 8)} />
        <List label="CTA" values={section.cta_patterns.slice(0, 3)} />
        <List label="Wymagane dowody" values={section.evidence_requirements.slice(0, 3)} />
      </div>
    </article>
  );
}

function List({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) return null;
  return (
    <div>
      <div className="font-semibold text-slate-700">{label}</div>
      <ul className="mt-1 list-disc space-y-1 pl-5">
        {values.map((value) => (
          <li key={value}>{value}</li>
        ))}
      </ul>
    </div>
  );
}

function formatCounts(counts: Record<string, number>) {
  const entries = Object.entries(counts);
  if (entries.length === 0) return "brak";
  return entries.map(([key, value]) => `${key}: ${value}`).join(", ");
}

function reviewDecisionLabel(value: string) {
  return REVIEW_DECISION_LABELS[value] ?? humanizeEnum(value);
}
