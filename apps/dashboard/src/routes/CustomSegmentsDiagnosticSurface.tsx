import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import { AdsDiagnosticsResponse, getAdsDiagnostics } from "../lib/api";
import { ActionPreviewCard } from "../components/ActionPreviewCard";
import { BlockerNotice, LabelChipRow, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";

type AdsCustomSegmentCandidate =
  AdsDiagnosticsResponse["custom_segments_read_contract"]["candidates"][number];
type AdsCustomSegmentAudienceForecastRow =
  AdsDiagnosticsResponse["custom_segments_read_contract"]["audience_forecast_read_contract"]["forecast_rows"][number];

export function AdsCustomSegmentCandidatesPanel({
  candidates,
  compact = false
}: {
  candidates: AdsCustomSegmentCandidate[];
  compact?: boolean;
}) {
  if (candidates.length === 0) {
    return compact ? null : (
      <BlockerNotice message="Brak segmentów do sprawdzenia. WILQ potrzebuje realnych wyszukiwanych haseł i sprawdzenia Keyword Planner, zanim przygotuje podgląd zmian." />
    );
  }
  return (
    <div className={compact ? "mt-3 grid gap-2" : "rounded-md border border-line bg-slate-50 p-3"}>
      {!compact ? (
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-ink">
            Segmenty do sprawdzenia z wyszukiwanych haseł
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            To jest kolejka tylko do przygotowania. WILQ nie twierdzi, że segment
            ma zasięg, zwrot z reklam albo wpływ na kampanię bez osobnej prognozy i sprawdzenia.
          </p>
        </div>
      ) : null}
      <div className={compact ? "grid gap-2" : "grid gap-3 md:grid-cols-2"}>
        {candidates.slice(0, compact ? 2 : 6).map((candidate) => {
          const rejectionEntries = Object.entries(
            candidate.source_quality.rejection_reason_labels
          );
          return (
          <article key={candidate.id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">{candidate.name}</h4>
                <LabelChipRow
                  className="mt-1"
                  chips={[
                    { label: "Cel segmentu", value: candidate.intent },
                    { label: "Pewność", value: candidate.confidence_label }
                  ]}
                />
              </div>
              <LabelChipRow
                chips={[
                  { label: "Priorytet", value: candidate.review_priority },
                  { label: "Ocena WILQ", value: candidate.review_score }
                ]}
              />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {candidate.review_reason}
            </p>
            <div className="mt-2 rounded-md border border-amber-100 bg-amber-50 p-2 text-xs leading-5 text-slate-700">
              <div className="font-semibold uppercase tracking-normal text-amber-700">
                Jakość źródeł
              </div>
              <div className="mt-1 flex flex-wrap gap-2">
                <span>przyjęte: {candidate.source_quality.accepted_terms}</span>
                <span>odrzucone: {candidate.source_quality.rejected_terms}</span>
                <span>braki metryk: {candidate.source_quality.missing_metric_terms}</span>
              </div>
              {rejectionEntries.length > 0 ? (
                <div className="mt-1 text-slate-600">
                  Powody:{" "}
                  {rejectionEntries
                    .slice(0, 3)
                    .map(([reason, count]) => `${reason} (${count})`)
                    .join(", ")}
                </div>
              ) : null}
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              Sprawdzenie w WILQ: {candidate.validation_status_label}
            </p>
            <p className="mt-2 text-sm font-medium text-ink">{candidate.next_step}</p>
            {candidate.preview_card ? (
              <div className="mt-2">
                <ActionPreviewCard card={candidate.preview_card} />
              </div>
            ) : null}
            {candidate.keyword_planner_ideas.length > 0 ? (
              <div className="mt-2 rounded-md border border-emerald-100 bg-emerald-50 p-2 text-xs leading-5 text-slate-700">
                <div className="font-semibold uppercase tracking-normal text-emerald-700">
                  Wzbogacenie Keyword Planner
                </div>
                <div className="mt-1 grid gap-1">
                  {candidate.keyword_planner_ideas.slice(0, compact ? 2 : 4).map((idea) => (
                    <div key={`${candidate.id}-${idea.idea_text}`} className="text-slate-700">
                      <div className="font-medium text-ink">{idea.idea_text}</div>
                      <LabelChipRow
                        className="mt-1"
                        chips={[
                          { label: "Średnie miesięczne wyszukiwania", value: idea.avg_monthly_searches },
                          { label: "Konkurencja", value: idea.competition }
                        ]}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="mt-2 grid gap-2 text-xs text-slate-600">
              <TraceLine
                label="Ocena człowieka"
                values={candidate.human_review_gate_labels}
                empty="brak oceny człowieka"
              />
              <TraceLine label="Hasła źródłowe" values={candidate.source_terms.slice(0, 8)} />
              <TraceLine label="Odrzucone" values={candidate.rejected_terms.slice(0, 6)} />
              <TraceLine
                label="Dowody"
                values={[candidate.evidence_summary_label]}
                empty="brak dowodów źródłowych"
              />
              <TraceLine
                label="Nie wolno twierdzić"
                values={candidate.blocked_claim_labels}
              />
            </div>
          </article>
          );
        })}
      </div>
    </div>
  );
}

export function AdsCustomSegmentAudienceForecastPanel({
  rows,
  compact = false
}: {
  rows: AdsCustomSegmentAudienceForecastRow[];
  compact?: boolean;
}) {
  if (rows.length === 0) {
    return compact ? null : (
      <BlockerNotice message="Brak wierszy prognozy i rozmiaru odbiorców. WILQ nie może ocenić zasięgu segmentów bez osobnego kontraktu odczytu." />
    );
  }
  return (
    <div className={compact ? "mt-3 grid gap-2" : "rounded-md border border-line bg-slate-50 p-3"}>
      {!compact ? (
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-ink">
            Prognoza i rozmiar odbiorców segmentów
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            To jest kontrakt bezpieczeństwa. Wiersz oznacza, że propozycja została
            sprawdzony, ale WILQ nadal nie ma dowodu zasięgu ani prognozy.
          </p>
        </div>
      ) : null}
      <div className={compact ? "grid gap-2" : "grid gap-3 md:grid-cols-2"}>
        {rows.slice(0, compact ? 2 : 6).map((row) => (
          <article key={row.id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">
                  {row.custom_segment_name}
                </h4>
                <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                  {row.status === "ready" ? "prognoza gotowa" : "brak prognozy"}
                </p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                odbiorcy:{" "}
                {typeof row.audience_size === "number"
                  ? row.audience_size
                  : "brak prognozy odbiorców"}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{row.reason}</p>
            <div className="mt-2 grid gap-2 text-xs text-slate-600">
              <TraceLine label="Hasła źródłowe" values={row.source_terms.slice(0, 8)} />
              <TraceLine
                label="Dowody"
                values={[row.evidence_summary_label]}
                empty="brak dowodów źródłowych"
              />
              <TraceLine
                label="Nie wolno twierdzić"
                values={row.blocked_claim_labels}
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

export function CustomSegmentsDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["ads-diagnostics", "custom-segments"],
    queryFn: getAdsDiagnostics
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać danych Ads. Segmenty nie mogą być oceniane bez WILQ." />
      </main>
    );
  }

  const data = diagnostics.data;
  const contract = data.custom_segments_read_contract;
  const audienceForecast = contract.audience_forecast_read_contract;
  const keywordPlanner = data.keyword_planner_read_contract;
  const sourceTermCount = contract.candidates.reduce(
    (total, candidate) => total + candidate.source_terms.length,
    0,
  );
  const rejectedTermCount = contract.candidates.reduce(
    (total, candidate) => total + candidate.rejected_terms.length,
    0,
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Segmenty z haseł</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok propozycji segmentów z wyszukiwanych haseł Google Ads.
            WILQ pokazuje tylko hasła źródłowe z dowodami i podgląd zmian do
            oceny; zasięg, wzrost konwersji, zwrot z reklam i zapis kierowania pozostają zablokowane.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
          <MetricTile label="Segmenty" value={contract.candidates.length} />
          <MetricTile label="Hasła źródłowe" value={sourceTermCount} />
          <MetricTile label="Odrzucone" value={rejectedTermCount} />
          <MetricTile label="Pomysły Keyword Planner" value={keywordPlanner.idea_rows.length} />
          <MetricTile label="Prognoza" value={audienceForecast.forecast_row_count} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status segmentów i dowodów z wyszukiwanych haseł
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
              {contract.summary}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <StatusBadge value={contract.status} label={contract.status_label} />
            <StatusBadge value={keywordPlanner.status} label={keywordPlanner.status_label} />
            <StatusBadge value={audienceForecast.status} label={audienceForecast.status_label} />
          </div>
        </div>
        <p className="mt-3 text-sm font-medium text-ink">{contract.next_step}</p>
        <p className="mt-2 text-xs leading-5 text-slate-600">
          Keyword Planner: {keywordPlanner.summary}
        </p>
        <p className="mt-1 text-xs leading-5 text-slate-600">
          Prognoza i rozmiar odbiorców: {audienceForecast.summary}
        </p>
      </section>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
              Segmenty do sprawdzenia
            </div>
            <h2 className="mt-1 text-base font-semibold tracking-normal">
              Co marketer może przygotować teraz
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Użyj propozycji tylko jako listy do oceny. Odrzuć frazy brandowe,
              niskointencyjne lub zbyt szerokie, a przed zapisem zmian wymagaj
              wzbogacenia Keyword Planner, prognozy i potwierdzenia człowieka.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-center text-xs">
            <MetricTile
              label="Brakujące dane"
              value={contract.missing_read_contract_summary_label}
            />
            <MetricTile
              label="Warunki sprawdzenia"
              value={contract.operator_review_gate_summary_label}
            />
          </div>
        </div>
        <AdsCustomSegmentCandidatesPanel candidates={contract.candidates} />
        <div className="mt-4">
          <AdsCustomSegmentAudienceForecastPanel
            rows={audienceForecast.forecast_rows}
            compact
          />
        </div>
      </section>

      <section className="rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Dowody i warunki segmentów
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
              Ten ekran nie służy do tworzenia odbiorców bez sprawdzenia. Pokazuje
              tylko kontrakt WILQ do ręcznej oceny.
            </p>
          </div>
        </div>
        <div className="grid gap-2 text-xs text-slate-600">
          <TraceLine
            label="Brakujące warunki sprawdzenia"
            values={uniqueValues([
              ...contract.missing_read_contract_labels,
              ...audienceForecast.missing_read_contract_labels
            ])}
          />
            <TraceLine
              label="Wymaga oceny"
              values={uniqueValues([
                ...contract.operator_review_gate_labels,
                ...audienceForecast.operator_review_gate_labels
              ])}
            />
          <TraceLine
            label="Nie wolno twierdzić"
            values={uniqueValues([
              ...contract.blocked_claim_labels,
              ...audienceForecast.blocked_claim_labels
            ])}
          />
          <TraceLine label="Źródła" values={[data.connector.label]} />
          <TraceLine
            label="Dowody"
            values={[contract.evidence_summary_label]}
          />
          <TraceLine
            label="Akcje do sprawdzenia"
            values={[contract.action_summary_label]}
          />
          <TraceLine label="Tryb Codexa" values={["Segmenty z haseł"]} />
        </div>
      </section>
    </main>
  );
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
