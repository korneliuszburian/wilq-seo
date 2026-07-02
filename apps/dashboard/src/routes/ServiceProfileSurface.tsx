import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, LockKeyhole, ShieldCheck } from "lucide-react";

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

type ServiceSection = ContentServiceProfileResponse["service_sections"][number];
type CoverageGap = ContentServiceProfileResponse["coverage_gaps"][number];
type ReviewAction = ContentServiceProfileResponse["review_actions"][number];
type ReviewActionSummary = ContentServiceProfileResponse["review_action_summary"];
type PrivateProposal = ContentServiceProfileResponse["private_source_proposals"][number];

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
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Profil usług Ekologus</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Read-only przegląd tego, co WILQ wie o usługach, claimach i wymaganych
            dowodach. Ten widok nie edytuje kart i nie promuje faktów do production-depth.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          <MetricTile label="Karty" value={data.coverage_summary.card_count} />
          <MetricTile label="Usługi" value={data.coverage_summary.service_card_count} />
          <MetricTile
            label="Do review"
            value={data.coverage_summary.source_backed_review_required_count}
          />
          <MetricTile label="Luki" value={data.coverage_summary.missing_required_area_count} />
        </div>
      </div>

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
                ? "production-depth gotowe"
                : "production-depth zablokowane",
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

      <ReviewActions actions={data.review_actions} summary={data.review_action_summary} />

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
            `${data.private_source_proposal_summary.claim_policy_proposal_count} claim-policy`,
            data.private_source_proposal_summary.evidence_requirement_proposal_count > 0
              ? `${data.private_source_proposal_summary.evidence_requirement_proposal_count} evidence-policy`
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
        <PrivateProposalCards proposals={data.private_source_proposals} />
        <details className="mt-4 text-xs text-slate-500">
          <summary className="cursor-pointer font-semibold text-slate-600">Szczegóły techniczne</summary>
          <div className="mt-2 space-y-1">
            <p>Endpoint kart: {data.technical_trace.knowledge_card_endpoint}</p>
            <p>Source facts: {data.technical_trace.source_fact_count}</p>
            <p>Protokół: {data.technical_trace.private_source_protocol_doc}</p>
          </div>
        </details>
      </section>
    </main>
  );
}

function PrivateProposalCards({ proposals }: { proposals: PrivateProposal[] }) {
  if (proposals.length === 0) return null;
  return (
    <div className="mt-4 grid gap-3 lg:grid-cols-2">
      {proposals.map((proposal) => (
        <article key={proposal.proposal_id} className="rounded-md border border-line p-3">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold">{proposal.target_card_title}</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                {proposal.source_locator_label}
              </p>
            </div>
            <span className="rounded-md border border-line px-2 py-0.5 text-xs text-slate-600">
              {proposal.review_status}
            </span>
          </div>
          <PlainChipRow
            className="mt-3"
            values={[
              proposal.source_type,
              proposal.privacy_class,
              `scope: ${proposal.scope}`,
              proposal.source_class_label,
              `support: ${proposal.support_level}`,
              `risk: ${proposal.risk_tier}`,
              proposal.confidence_label,
              proposal.promotion_allowed ? "promocja dozwolona" : "bez promocji"
            ]}
          />
          <p className="mt-2 text-sm leading-6 text-slate-600">{proposal.safe_next_step}</p>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            {proposal.blocked_write_claim}
          </p>
          <List label="Claimy zablokowane" values={proposal.blocked_claims} />
          <p className="mt-2 text-xs leading-5 text-slate-500">
            Rola review: {proposal.owner_role}
          </p>
        </article>
      ))}
    </div>
  );
}

function CoverageGaps({ gaps }: { gaps: CoverageGap[] }) {
  if (gaps.length === 0) return null;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-normal text-slate-700">
        <AlertTriangle aria-hidden="true" size={16} />
        Luki do review
      </div>
      <div className="mt-4 grid gap-3">
        {gaps.map((gap) => (
          <div key={gap.gap_id} className="rounded-md border border-wait/30 bg-wait/10 p-3">
            <h3 className="text-sm font-semibold text-wait">{gap.label}</h3>
            <p className="mt-1 text-sm leading-6 text-slate-700">{gap.reason}</p>
            <p className="mt-1 text-sm leading-6 text-slate-600">{gap.safe_next_step}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function ReviewActions({
  actions,
  summary
}: {
  actions: ReviewAction[];
  summary: ReviewActionSummary;
}) {
  if (actions.length === 0) return null;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
        Akcje review
      </h2>
      <PlainChipRow
        className="mt-3"
        values={[
          `${summary.total_count} razem`,
          `${summary.public_service_review_count} publicznych usług`,
          `${summary.private_service_review_count} prywatne service`,
          `${summary.private_policy_review_count} prywatne claim-policy`,
          `${summary.review_request_count} review request`,
          summary.prepare_count > 0 ? `${summary.prepare_count} prepare` : null
        ]}
      />
      <p className="mt-2 text-sm leading-6 text-slate-600">{summary.safe_next_step}</p>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {actions.map((action) => (
          <div key={action.action_id} className="rounded-md border border-line p-3">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold">{action.label}</h3>
              <span className="rounded-md border border-line px-2 py-0.5 text-xs text-slate-600">
                {action.mode}
              </span>
              <span className="rounded-md border border-line px-2 py-0.5 text-xs text-slate-600">
                {action.review_scope}
              </span>
              <span className="rounded-md border border-line px-2 py-0.5 text-xs text-slate-600">
                {action.priority}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600">{action.reason}</p>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              {action.blocked_write_claim}
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              Rola: {action.required_human_role}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
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
