import { BlockerNotice, MetricTile } from "../../components/OperatorPrimitives";
import type {
  Ga4DecisionCardComponent,
  Ga4DiagnosticsResponse
} from "./Shared";

export function Ga4MeasurementIssues({
  data,
  DecisionCard
}: {
  data: Ga4DiagnosticsResponse;
  DecisionCard: Ga4DecisionCardComponent;
}) {
  const measurementDecisions = data.decision_queue.filter(
    (decision) => decision.decision_type === "fix_measurement"
  );

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Problemy pomiaru GA4
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Braki w wymiarach raportu są problemem pomiaru lub atrybucji. WILQ pokazuje je
            osobno, żeby nie mieszać ich z oceną jakości strony wejścia albo kampanii.
          </p>
        </div>
        <MetricTile label="Do kontroli" value={measurementDecisions.length} />
      </div>
      {measurementDecisions.length > 0 ? (
        <div className="grid gap-3 xl:grid-cols-2">
          {measurementDecisions.slice(0, 4).map((decision) => (
            <DecisionCard key={`measurement-${decision.id}`} decision={decision} />
          ))}
        </div>
      ) : (
        <BlockerNotice message="Brak aktywnych problemów pomiaru w top kolejce GA4. Wnioski o konwersjach, zwrot z reklam i przychody nadal pozostają zablokowane bez właściwych metryk." />
      )}
    </section>
  );
}
