import { useQuery } from "@tanstack/react-query";
import { ClipboardCheck } from "lucide-react";

import { AhrefsDiagnosticsResponse, getAhrefsDiagnostics } from "../lib/api";
import { DiagnosticDecisionCard } from "../components/DiagnosticDecisionCard";
import {
  DiagnosticSurfaceShell,
  DiagnosticSurfaceUnavailable
} from "../components/DiagnosticSurfaceShell";
import {
  BlockerNotice,
  LoadingBand,
  MetricTile,
  PlainChipRow
} from "../components/OperatorPrimitives";
import { TraceLine } from "../components/TraceLine";

type AhrefsDecisionItem = AhrefsDiagnosticsResponse["decision_queue"][number];

const AHREFS_VISIBLE_GAP_RECORD_LIMIT = 8;

export function AhrefsDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["ahrefs-diagnostics"],
    queryFn: getAhrefsDiagnostics
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <DiagnosticSurfaceUnavailable message="Nie udało się odczytać danych Ahrefs. Ten widok nie może udawać luk treści, linków zwrotnych ani przewagi konkurencji bez WILQ." />
    );
  }

  const data = diagnostics.data;
  const latestRefresh = data.latest_refresh;

  return (
    <DiagnosticSurfaceShell
      title="Ahrefs"
      description="Dedykowany widok Ahrefs z WILQ. Oddziela kontekst autorytetu od konkretnych luk treści, linków zwrotnych i konkurencji, żeby marketer nie dostał generycznej rekomendacji SEO z samej oceny domeny."
      metrics={
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Autorytet" value={data.authority_fact_count} />
          <MetricTile label="Luki SEO" value={data.gap_fact_count} />
          <MetricTile label="Blokady" value={data.blocker_count} />
        </div>
      }
    >

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Ahrefs i dowody SEO
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <PlainChipRow
            values={[
              `${data.connector.label || "Ahrefs"}: ${data.connector_status_label}`,
              data.live_data_status_label,
              latestRefresh ? `ostatni odczyt danych: ${data.latest_refresh_status_label}` : null
            ]}
          />
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
    </DiagnosticSurfaceShell>
  );
}

function AhrefsOperatorSummary({ data }: { data: AhrefsDiagnosticsResponse }) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const decisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is AhrefsDecisionItem => Boolean(decision));
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            {summary.title}
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {summary.summary}
          </p>
        </div>
      </div>
      {decisions.length === 0 ? (
        <BlockerNotice message="Brak decyzji Ahrefs w WILQ. Widok nie wygeneruje analizy luk z pustego stanu." />
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
    <DiagnosticDecisionCard
      id={decision.id}
      chips={[
        { label: "Źródło", value: "Ahrefs" },
        { label: "Typ", value: decision.decision_type_label || "decyzja" },
        { label: "Priorytet", value: decision.priority_label }
      ]}
      title={decision.title}
      statusLabel={decision.status_label}
      summary={decision.summary}
      rationale={decision.rationale}
      nextStep={decision.next_step}
      metricTiles={Object.entries(decision.metric_tiles)}
    >
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine
          label="Na czym można się oprzeć"
          values={decision.allowed_evidence_labels}
        />
        <TraceLine
          label="Brakujące dane"
          values={decision.missing_read_contract_labels}
          empty="dane kompletne"
        />
        <TraceLine
          label="Czego nie wolno obiecać"
          values={decision.blocked_claim_labels}
        />
        <TraceLine
          label="Dowody"
          values={[decision.evidence_summary_label]}
          empty="WILQ nie podał dowodów źródłowych; Ahrefs zostaje kontekstem, nie decyzją."
        />
      </div>
    </DiagnosticDecisionCard>
  );
}

function AhrefsGapContractPanel({ data }: { data: AhrefsDiagnosticsResponse }) {
  const contract = data.gap_read_contract;
  const visibleGapRecords = contract.gap_records.slice(0, AHREFS_VISIBLE_GAP_RECORD_LIMIT);
  return (
    <section className="mt-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Luki SEO z Ahrefs
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">{contract.summary}</p>
        </div>
        <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-ink">
          {contract.status_label}
        </span>
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        <MetricTile label="Luki do sprawdzenia" value={contract.gap_records.length} />
        <MetricTile label="Brakujące dane" value={contract.missing_read_contract_summary_label} />
        <MetricTile label="Zablokowane obietnice" value={contract.blocked_claim_summary_label} />
        <MetricTile
          label="Dopasowania GSC"
          value={contract.cross_check_gsc_match_count}
        />
        <MetricTile
          label="Dopasowania WordPress"
          value={contract.cross_check_wordpress_match_count}
        />
        <MetricTile label="Cross-check" value={contract.cross_check_status_label} />
      </div>
      <p className="mt-3 text-sm font-semibold leading-6 text-ink">{contract.next_step}</p>
      {contract.cross_check_summary ? (
        <div className="mt-3 rounded-md border border-line bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
              Sprawdzenie GSC i WordPress
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-700">
            {contract.cross_check_summary}
          </p>
          <p className="mt-2 text-xs font-semibold leading-5 text-ink">
            {contract.cross_check_next_step}
          </p>
          {contract.cross_check_candidates.length > 0 ? (
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {contract.cross_check_candidates.slice(0, 4).map((candidate) => (
                <article key={candidate.id} className="rounded-md border border-line bg-white p-3">
                  <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                {candidate.gap_type_label || "propozycja Ahrefs"}
                  </p>
                  <h3 className="mt-1 text-sm font-semibold">{candidate.topic}</h3>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
                    <span className="rounded-md border border-line px-2 py-1">
                      GSC: {candidate.gsc_cross_check.label}
                    </span>
                    <span className="rounded-md border border-line px-2 py-1">
                      WP: {candidate.wordpress_cross_check.label}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-700">
                    {candidate.next_step}
                  </p>
                </article>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine
          label="Brakujące dane"
          values={contract.missing_read_contract_labels}
          empty="dane kompletne"
        />
        <TraceLine
          label="Co trzeba sprawdzić"
          values={contract.operator_review_gate_labels}
        />
        <TraceLine
          label="Czego nie wolno obiecać"
          values={contract.blocked_claim_labels}
        />
        <TraceLine
          label="Dowody"
          values={[contract.evidence_summary_label]}
          empty="WILQ nie podał dowodów źródłowych; nie traktuj luki jako rekomendacji."
        />
      </div>
      {contract.gap_records.length === 0 ? (
        <BlockerNotice message="Brak konkretnych luk z Ahrefs. Ahrefs może wspierać ocenę treści tylko jako kontekst autorytetu, nie jako lista przewag konkurencji." />
      ) : (
        <>
          <p className="mt-3 text-xs font-medium text-slate-600">
            Pokazuję top {visibleGapRecords.length} z {contract.gap_records.length} rekordów.
          </p>
          <div className="mt-3 grid gap-3 xl:grid-cols-2">
            {visibleGapRecords.map((record) => (
              <article key={record.id} className="rounded-md border border-line p-3">
                <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  {record.gap_type_label || "rekord Ahrefs"}
                </p>
                <h3 className="mt-1 text-sm font-semibold">{record.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-700">{record.summary}</p>
                <p className="mt-2 text-xs font-semibold leading-5 text-ink">
                  {record.next_step}
                </p>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function AhrefsDiagnosticProof({ data }: { data: AhrefsDiagnosticsResponse }) {
  return (
    <section className="mt-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
          Dowody i warunki analizy Ahrefs
        </h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          WILQ pokazuje dane autorytetu osobno od konkretnych luk SEO. Brak luk
          oznacza brak diagnozy luk konkurencji, nie zaproszenie do zgadywania.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {data.sections.map((section) => (
          <article key={section.id} className="rounded-md border border-line p-3">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold">{section.title}</h3>
              <span className="rounded-md border border-line px-2 py-1 text-xs text-slate-600">
                {section.status_label}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{section.summary}</p>
            <p className="mt-2 text-xs leading-5 text-slate-600">{section.next_step}</p>
          </article>
        ))}
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <MetricTile label="Dowody" value={data.evidence_summary_label} />
        <TraceLine label="Źródła danych" values={data.source_connector_labels} />
        <TraceLine
          label="Czego nie wolno obiecać"
          values={uniqueValues(
            data.decision_queue.flatMap((decision) =>
              decision.blocked_claim_labels
            )
          )}
        />
      </div>
    </section>
  );
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
