import { AdsDiagnosticsResponse } from "../lib/api";
import { adsCost, adsNumber } from "../lib/adsFormatting";
import { adsMissingAdGroupLabel, adsMissingCampaignLabel } from "../lib/adsLabels";
import { ActionPreviewCard } from "./ActionPreviewCard";
import { BlockerNotice, LabelChipRow, MetricTile } from "./OperatorPrimitives";
import { LinkedTraceLine, TraceLine } from "./TraceLine";

type AdsNegativeKeywordCandidate =
  AdsDiagnosticsResponse["negative_keywords_read_contract"]["candidates"][number];

export function AdsNegativeKeywordCandidatesPanel({
  candidates,
  currencyCode,
  compact = false
}: {
  candidates: AdsNegativeKeywordCandidate[];
  currencyCode?: string;
  compact?: boolean;
}) {
  if (candidates.length === 0) {
    return compact ? null : (
      <BlockerNotice message="Brak kolejki oceny wykluczeń. WILQ potrzebuje wyszukiwanych haseł z aktywnością i zerową konwersją, a potem 90-dniowej kontroli bezpieczeństwa." />
    );
  }
  return (
    <div className={compact ? "mt-3 grid gap-2" : "rounded-md border border-line bg-slate-50 p-3"}>
      {!compact ? (
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-ink">
            Ocena wykluczeń z wyszukiwanych haseł
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            To jest kolejka bezpieczeństwa. WILQ pokazuje terminy do sprawdzenia,
            ale blokuje zapis wykluczeń bez kontekstu dopasowania, 90-dniowej
            historii i sprawdzenia w WILQ.
          </p>
        </div>
      ) : null}
      <div className={compact ? "grid gap-2" : "grid gap-3 md:grid-cols-2"}>
        {candidates.slice(0, compact ? 2 : 6).map((candidate) => (
          <article key={candidate.id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">{candidate.search_term}</h4>
                <LabelChipRow
                  className="mt-1"
                  chips={[
                    { label: "Kampania", value: candidate.campaign_label || adsMissingCampaignLabel },
                    { label: "Grupa reklam", value: candidate.ad_group_label || adsMissingAdGroupLabel }
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
            <p className="mt-1 text-xs leading-5 text-slate-600">
              Bezpieczeństwo:{" "}
              {candidate.safety_status_label ||
                "WILQ nie podał statusu bezpieczeństwa; zostaw to jako ręczny przegląd"}
            </p>
            <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
              <MetricTile label="Kliknięcia" value={adsNumber(candidate.clicks)} />
              <MetricTile
                label="Koszt"
                value={adsCost(candidate.cost_micros, currencyCode)}
              />
              <MetricTile label="Konwersje" value={adsNumber(candidate.conversions)} />
              <MetricTile label="Klik. 90d" value={adsNumber(candidate.clicks_90d)} />
              <MetricTile
                label="Koszt 90d"
                value={adsCost(candidate.cost_micros_90d, currencyCode)}
              />
              <MetricTile label="Konw. 90d" value={adsNumber(candidate.conversions_90d)} />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {candidate.next_step}
            </p>
            {candidate.preview_card ? (
              <div className="mt-2">
                <ActionPreviewCard card={candidate.preview_card} />
              </div>
            ) : null}
            {candidate.keyword_context_rows.length > 0 ? (
              <div className="mt-2 rounded-md border border-line bg-slate-50 p-2 text-xs leading-5 text-slate-700">
                <div className="font-semibold uppercase tracking-normal text-slate-600">
                  Istniejące słowa kluczowe w tej grupie
                </div>
                {candidate.keyword_context_rows.slice(0, 4).map((row) => (
                  <LabelChipRow
                    key={`${row.criterion_id ?? row.keyword_text}-${row.match_type}`}
                    className="mt-1"
                    chips={[
                      { label: "Słowo", value: row.keyword_text },
                      { label: "Dopasowanie", value: row.match_type_label },
                      { label: "Status", value: row.negative_label }
                    ]}
                  />
                ))}
              </div>
            ) : null}
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <TraceLine
                label="Ocena człowieka"
                values={candidate.human_review_gate_labels}
                empty="WILQ nie ma oceny człowieka; nie wykonuj zmiany bez review."
              />
              <TraceLine label="Wymagane kontrole" values={candidate.required_check_labels} />
              <LinkedTraceLine
                label="Dowody"
                values={[...new Set([
                  ...candidate.evidence_ids,
                  ...candidate.safety_evidence_ids
                ])].slice(0, 3)}
                kind="evidence"
              />
              <TraceLine label="Nie wolno twierdzić" values={candidate.blocked_claim_labels} />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
