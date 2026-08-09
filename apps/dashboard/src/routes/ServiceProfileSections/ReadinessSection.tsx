import type { ComponentType } from "react";

import { MetricTile, PlainChipRow } from "../../components/OperatorPrimitives";
import type { ContentServiceProfileResponse } from "../../lib/api";
import {
  operatorText,
  priorityLabel,
  reviewScopeLabel,
  type ApprovalReadiness
} from "./Shared";

type SourceFactCoverage = ContentServiceProfileResponse["source_fact_coverage"];
type PrivateReviewValue = ContentServiceProfileResponse["private_review_value"];
type ListComponent = ComponentType<{ label: string; values: string[] }>;

export function ApprovalReadinessPanel({
  readiness
}: {
  readiness: ApprovalReadiness;
}) {
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Gotowość zatwierdzenia wiedzy
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal text-ink">
            {readiness.status_label}
          </h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
            {readiness.safe_next_step}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          <MetricTile label="Zatwierdzone" value={readiness.approved_current_count} />
          <MetricTile label="Do review" value={readiness.review_required_count} />
          <MetricTile label="Blokady" value={readiness.blockers.length} />
          <MetricTile
            label="Wniosek"
            value={readiness.can_request_promotion ? "gotowy" : "stop"}
          />
        </div>
      </div>

      <PlainChipRow
        className="mt-3"
        values={[
          readiness.can_request_promotion
            ? "można przygotować wniosek"
            : "wniosek zablokowany",
          readiness.mutation_allowed ? "mutacja dostępna" : "bez mutacji",
          readiness.production_depth_unlocked
            ? "wiedza produkcyjna odblokowana"
            : "wiedza produkcyjna zablokowana",
          readiness.reviewed_output_required ? "wymaga decyzji review" : null,
          readiness.first_action_label ? `zacznij: ${readiness.first_action_label}` : null
        ]}
      />

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {readiness.checklist.map((item) => (
          <article
            key={item.code}
            className={[
              "rounded-md border p-3",
              item.blocking ? "border-wait/30 bg-wait/10" : "border-line bg-slate-50"
            ].join(" ")}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="text-sm font-semibold text-ink">{item.label}</h3>
              <span className="rounded-md border border-line bg-white px-2 py-0.5 text-xs text-slate-600">
                {approvalReadinessStatusLabel(item.status)}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{item.detail}</p>
            <p className="mt-2 text-sm font-medium leading-6 text-ink">{item.next_step}</p>
            {item.related_action_id ? (
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Powiązana akcja do sprawdzenia: {item.related_action_id}
              </p>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

export function SourceFactCoveragePanel({
  coverage,
  privateReviewValue,
  List,
  formatCounts
}: {
  coverage: SourceFactCoverage;
  privateReviewValue: PrivateReviewValue;
  List: ListComponent;
  formatCounts: (counts: Record<string, number>) => string;
}) {
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Audyt pokrycia wiedzy
          </div>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
            {coverage.safe_next_step}
          </p>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
            {privateReviewValue.value_summary}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          <MetricTile
            label="Wiedza produkcyjna"
            value={`${coverage.production_depth_percent}%`}
          />
          <MetricTile
            label="Usługi zatwierdzone"
            value={`${coverage.approved_service_percent}%`}
          />
          <MetricTile label="Fakty zatwierdzone" value={`${coverage.reviewed_fact_percent}%`} />
          <MetricTile
            label="Wartość ekologus-ai"
            value={`${privateReviewValue.operator_value_score}/10`}
          />
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Co to znaczy teraz</h3>
          <PlainChipRow
            className="mt-2"
            values={[
              coverage.pass_state ? "audyt spójny" : "audyt wymaga naprawy",
              coverage.ready_for_daily_content
                ? "treści dzienne gotowe"
                : "treści dzienne zablokowane",
              `${coverage.fact_count} faktów źródłowych`,
              `${coverage.review_action_count} akcji review`,
              `${coverage.private_review_required_count} prywatnych do review`
            ]}
          />
          <List
            label="Dlaczego ekologus-ai pomaga"
            values={privateReviewValue.review_value_points}
          />
          <List label="Pytania do Wilka" values={privateReviewValue.review_questions} />
          <List
            label="Co blokuje wiedzę produkcyjną"
            values={coverage.blockers.slice(0, 4).map(marketerKnowledgeLabel)}
          />
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Następne review</h3>
          {coverage.first_review_action_label ? (
            <p className="mt-2 text-sm leading-6 text-slate-700">
              Zacznij od:{" "}
              <span className="font-semibold text-ink">
                {coverage.first_review_action_label}
              </span>
            </p>
          ) : null}
          <ol className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
            {coverage.review_action_queue.slice(0, 4).map((item, index) => (
              <li key={item.action_id} className="grid grid-cols-[1.5rem_1fr] gap-2">
                <span className="font-semibold text-action">{index + 1}.</span>
                <span>
                  <span className="font-medium text-ink">{item.target_card_title}</span>
                  <span className="text-slate-500">
                    {" · "}
                    {reviewScopeLabel(item.review_scope)}
                    {" · "}
                    {priorityLabel(item.priority)}
                  </span>
                </span>
              </li>
            ))}
          </ol>
          <details className="mt-3 text-xs text-slate-500">
            <summary className="cursor-pointer font-semibold text-slate-600">
              Liczby techniczne
            </summary>
            <div className="mt-2 space-y-1">
              <p>Review statusy: {formatCounts(coverage.fact_review_counts)}</p>
              <p>Scope faktów: {formatCounts(coverage.fact_scope_counts)}</p>
              <p>Connectory: {formatCounts(coverage.fact_connector_counts)}</p>
            </div>
          </details>
        </div>
      </div>
    </section>
  );
}

function approvalReadinessStatusLabel(value: string) {
  if (value === "ready_for_promotion_request") return "gotowe do wniosku";
  if (value === "ready_for_review") return "gotowe do review";
  return "zablokowane";
}

function marketerKnowledgeLabel(value: string) {
  return operatorText(value)
    .replaceAll("production-depth", "wiedzy produkcyjnej")
    .replaceAll("review-required", "wymagająca oceny")
    .replaceAll("approved-current", "zatwierdzona")
    .replaceAll("review", "ocena");
}
