import { useQuery } from "@tanstack/react-query";
import { ClipboardCheck } from "lucide-react";

import { AhrefsDiagnosticsResponse, getAhrefsDiagnostics } from "../lib/api";
import { MetricFactChips } from "../components/MetricFactChips";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import { priorityLabel } from "./marketingLabels";

type AhrefsDecisionItem = AhrefsDiagnosticsResponse["decision_queue"][number];

export function AhrefsDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["ahrefs-diagnostics"],
    queryFn: getAhrefsDiagnostics
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/ahrefs/diagnostics. Ahrefs route nie może udawać luki treści, luki backlinków ani przewagi konkurencji bez WILQ API." />
      </main>
    );
  }

  const data = diagnostics.data;
  const latestRefresh = data.latest_refresh;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Ahrefs</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Ahrefs z WILQ API. Oddziela kontekst autorytetu od
            prawdziwych rekordów luk treści, backlinków i konkurencji, żeby marketer nie
            dostał generycznej rekomendacji SEO z samego DR.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Autorytet" value={data.authority_fact_count} />
          <MetricTile label="Luki SEO" value={data.gap_fact_count} />
          <MetricTile label="Blockery" value={data.blocker_count} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Ahrefs / dowody SEO
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.connector.id}: {ahrefsConnectorStatusLabel(data.connector.status)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "metryki Ahrefs dostępne" : "brak metryk Ahrefs"}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {ahrefsRefreshStatusLabel(latestRefresh.status)}
              </span>
            ) : null}
          </div>
        </div>
        {latestRefresh?.errors.length ? (
          <div className="mt-3 rounded-md border border-risk/30 bg-risk/10 p-3 text-sm text-risk">
            {latestRefresh.errors[0]}
          </div>
        ) : null}
      </section>

      <AhrefsOperatorSummary data={data} />
      <AhrefsGapContractPanel data={data} />
      <AhrefsDiagnosticProof data={data} />
    </main>
  );
}

function AhrefsOperatorSummary({ data }: { data: AhrefsDiagnosticsResponse }) {
  const decisions = [...data.decision_queue].sort(ahrefsDecisionSortValue);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Co marketer ma wiedzieć o Ahrefs
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Ten widok nie jest listą connectorów. Pokazuje, czy Ahrefs może już
            wesprzeć decyzje SEO i które claimy nadal są zablokowane.
          </p>
        </div>
      </div>
      {decisions.length === 0 ? (
        <BlockerNotice message="Brak decyzji Ahrefs z WILQ API. Widok nie wygeneruje analizy luk z pustego stanu." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {decisions.map((decision) => (
            <AhrefsDecisionCard key={decision.id} decision={decision} />
          ))}
        </div>
      )}
    </section>
  );
}

function AhrefsDecisionCard({ decision }: { decision: AhrefsDecisionItem }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Ahrefs / {ahrefsDecisionTypeLabel(decision.decision_type)} /{" "}
            {priorityLabel(decision.priority)}
          </p>
          <h3 className="mt-1 text-base font-semibold">{decision.title}</h3>
        </div>
        <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-ink">
          {ahrefsDecisionStatusLabel(decision.status)}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{decision.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{decision.rationale}</p>
      <p className="mt-3 text-sm font-semibold leading-6 text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine
          label="Dozwolone evidence"
          values={decision.allowed_evidence.map(ahrefsAllowedEvidenceLabel)}
        />
        <TraceLine
          label="Brakujące kontrakty"
          values={decision.missing_read_contracts.map(ahrefsMissingContractLabel)}
        />
        <TraceLine
          label="Blokady claimów"
          values={decision.blocked_claims.map(ahrefsBlockedClaimLabel)}
        />
        <LinkedTraceLine label="Dowody" values={decision.evidence_ids} kind="evidence" />
      </div>
      {decision.metric_facts.length > 0 ? (
        <MetricFactChips facts={decision.metric_facts.slice(0, 6)} />
      ) : null}
    </article>
  );
}

function AhrefsGapContractPanel({ data }: { data: AhrefsDiagnosticsResponse }) {
  const contract = data.gap_read_contract;
  return (
    <section className="mt-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Kontrakt luk Ahrefs
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">{contract.summary}</p>
        </div>
        <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-ink">
          {ahrefsDecisionStatusLabel(contract.status)}
        </span>
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        <MetricTile label="Gap records" value={contract.gap_records.length} />
        <MetricTile label="Braki kontraktu" value={contract.missing_read_contracts.length} />
        <MetricTile label="Blokady claimów" value={contract.blocked_claims.length} />
      </div>
      <p className="mt-3 text-sm font-semibold leading-6 text-ink">{contract.next_step}</p>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine
          label="Brakujące kontrakty"
          values={contract.missing_read_contracts.map(ahrefsMissingContractLabel)}
        />
        <TraceLine
          label="Review gates"
          values={contract.operator_review_gates.map(ahrefsReviewGateLabel)}
        />
        <TraceLine
          label="Blokady claimów"
          values={contract.blocked_claims.map(ahrefsBlockedClaimLabel)}
        />
        <LinkedTraceLine label="Dowody" values={contract.evidence_ids} kind="evidence" />
      </div>
      {contract.gap_records.length === 0 ? (
        <BlockerNotice message="Brak typed gap records. Ahrefs może wspierać content review tylko jako kontekst autorytetu, nie jako lista luk konkurencji." />
      ) : (
        <div className="mt-3 grid gap-3 xl:grid-cols-2">
          {contract.gap_records.map((record) => (
            <article key={record.id} className="rounded-md border border-line p-3">
              <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                {record.gap_type}
              </p>
              <h3 className="mt-1 text-sm font-semibold">{record.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-700">{record.summary}</p>
              <p className="mt-2 text-xs font-semibold leading-5 text-ink">
                {record.next_step}
              </p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function AhrefsDiagnosticProof({ data }: { data: AhrefsDiagnosticsResponse }) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  return (
    <section className="mt-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
          Dowody i ograniczenia Ahrefs
        </h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          WILQ pokazuje fakty autorytetu osobno od rekordów luk SEO. Brak rekordów luk
          oznacza brak diagnozy luk konkurencji, nie zaproszenie do zgadywania.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {data.sections.map((section) => (
          <article key={section.id} className="rounded-md border border-line p-3">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold">{section.title}</h3>
              <span className="rounded-md border border-line px-2 py-1 text-xs text-slate-600">
                {ahrefsSectionStatusLabel(section.status)}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{section.summary}</p>
            <p className="mt-2 text-xs leading-5 text-slate-600">{section.next_step}</p>
          </article>
        ))}
      </div>
      {metricFacts.length > 0 ? <MetricFactChips facts={metricFacts.slice(0, 8)} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 8)} kind="evidence" />
        <TraceLine label="Źródła" values={["ahrefs"]} />
        <TraceLine
          label="Zablokowane claimy"
          values={uniqueValues(
            data.decision_queue.flatMap((decision) =>
              decision.blocked_claims.map(ahrefsBlockedClaimLabel)
            )
          )}
        />
      </div>
    </section>
  );
}

function ahrefsDecisionSortValue(decision: AhrefsDecisionItem) {
  const statusRank: Record<AhrefsDecisionItem["status"], number> = {
    ready: 0,
    blocked: 1
  };
  return statusRank[decision.status] * 1000 + decision.priority;
}

function ahrefsDecisionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  return status;
}

function ahrefsSectionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  if (status === "missing") return "brak facts";
  return status;
}

function ahrefsDecisionTypeLabel(value: string) {
  const labels: Record<string, string> = {
    block_gap_claims: "blokada luk",
    review_authority_context: "kontekst autorytetu",
    review_gap_records: "review rekordów luk",
    run_authority_read: "odczyt autorytetu"
  };
  return labels[value] ?? value;
}

function ahrefsReviewGateLabel(value: string) {
  const labels: Record<string, string> = {
    ahrefs_gap_records_required: "wymagane rekordy luk Ahrefs",
    content_planner_review_required: "review w Content Planner",
    human_strategy_review: "review strategii przez człowieka"
  };
  return labels[value] ?? value;
}

function ahrefsConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function ahrefsRefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  return status;
}

function ahrefsAllowedEvidenceLabel(value: string) {
  const labels: Record<string, string> = {
    ahrefs_rank: "Ahrefs Rank",
    authority_summary: "kontekst autorytetu",
    domain_rating: "Domain Rating"
  };
  return labels[value] ?? value;
}

function ahrefsMissingContractLabel(value: string) {
  const labels: Record<string, string> = {
    ahrefs_backlink_gap_records: "rekordy luk backlinków",
    ahrefs_competitor_pages: "strony konkurencji",
    ahrefs_content_gap_records: "rekordy luk treści",
    ahrefs_organic_keywords_by_url: "organiczne słowa per URL",
    ahrefs_top_pages_by_competitor: "top pages konkurencji",
    domain_rating: "Domain Rating"
  };
  return labels[value] ?? value;
}

function ahrefsBlockedClaimLabel(value: string) {
  const labels: Record<string, string> = {
    "authority improvement": "poprawa autorytetu",
    "backlink gap": "luka backlinków",
    "competitor gap": "przewaga konkurencji",
    "content gap": "luka treści",
    "ranking opportunity": "okazja rankingowa",
    "traffic uplift": "wzrost ruchu"
  };
  return labels[value] ?? value;
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
