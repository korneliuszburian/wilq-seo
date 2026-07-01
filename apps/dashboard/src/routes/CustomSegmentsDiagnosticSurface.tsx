import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import { getAdsDiagnostics } from "../lib/api";
import {
  AdsCustomSegmentAudienceForecastPanel,
  AdsCustomSegmentCandidatesPanel
} from "../components/AdsCustomSegmentPanels";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";

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
