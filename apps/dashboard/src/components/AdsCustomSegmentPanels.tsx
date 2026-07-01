import type { AdsDiagnosticsResponse } from "../lib/api";
import { ActionPreviewCard } from "./ActionPreviewCard";
import { BlockerNotice, LabelChipRow } from "./OperatorPrimitives";
import { TraceLine } from "./TraceLine";

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
                            {
                              label: "Średnie miesięczne wyszukiwania",
                              value: idea.avg_monthly_searches
                            },
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
                  empty="WILQ nie ma oceny człowieka; nie dodawaj segmentu bez review."
                />
                <TraceLine label="Hasła źródłowe" values={candidate.source_terms.slice(0, 8)} />
                <TraceLine label="Odrzucone" values={candidate.rejected_terms.slice(0, 6)} />
                <TraceLine
                  label="Dowody"
                  values={[candidate.evidence_summary_label]}
                  empty="WILQ nie podał dowodów źródłowych; nie traktuj segmentu jako gotowego kierowania."
                />
                <TraceLine label="Nie wolno twierdzić" values={candidate.blocked_claim_labels} />
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
                <h4 className="text-sm font-semibold text-ink">{row.custom_segment_name}</h4>
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
                empty="WILQ nie podał dowodów źródłowych; nie oceniaj zasięgu bez źródła."
              />
              <TraceLine label="Nie wolno twierdzić" values={row.blocked_claim_labels} />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
