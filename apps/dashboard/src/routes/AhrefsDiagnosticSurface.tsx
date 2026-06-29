import { useQuery } from "@tanstack/react-query";
import { ClipboardCheck } from "lucide-react";

import { AhrefsDiagnosticsResponse, getAhrefsDiagnostics } from "../lib/api";
import { BlockerNotice, LabelChipRow, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
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
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać danych Ahrefs. Ten widok nie może udawać luk treści, linków zwrotnych ani przewagi konkurencji bez WILQ." />
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
            Dedykowany widok Ahrefs z WILQ. Oddziela kontekst autorytetu od
            konkretnych luk treści, linków zwrotnych i konkurencji, żeby marketer nie
            dostał generycznej rekomendacji SEO z samej oceny domeny.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Autorytet" value={data.authority_fact_count} />
          <MetricTile label="Luki SEO" value={data.gap_fact_count} />
          <MetricTile label="Blokady" value={data.blocker_count} />
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
              {data.connector.label || "Ahrefs"}: {data.connector_status_label}
              <span className="sr-only">; </span>
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_status_label}
              <span className="sr-only">; </span>
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt danych: {data.latest_refresh_status_label}
                <span className="sr-only">; </span>
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
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <LabelChipRow
            chips={[
              { label: "Źródło", value: "Ahrefs" },
              { label: "Typ", value: decision.decision_type_label || "decyzja" },
              { label: "Priorytet", value: decision.priority_label }
            ]}
          />
          <h3 className="mt-1 text-base font-semibold">{decision.title}</h3>
        </div>
        <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-ink">
          {decision.status_label}
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
          label="Dozwolone dowody"
          values={decision.allowed_evidence_labels}
        />
        <TraceLine
          label="Brakujące dane"
          values={decision.missing_read_contract_labels}
        />
        <TraceLine
          label="Czego nie wolno obiecać"
          values={decision.blocked_claim_labels}
        />
        <TraceLine
          label="Dowody"
          values={[decision.evidence_summary_label]}
          empty="brak"
        />
      </div>
    </article>
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
      </div>
      <p className="mt-3 text-sm font-semibold leading-6 text-ink">{contract.next_step}</p>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine
          label="Brakujące dane"
          values={contract.missing_read_contract_labels}
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
          empty="brak"
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
