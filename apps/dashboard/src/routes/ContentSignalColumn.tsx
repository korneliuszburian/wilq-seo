import { Search } from "lucide-react";

import { ContentMapColumn } from "./ContentMapPrimitives";

type ContentSignalRow = {
  label: string;
  summary: string;
  tone: string;
};

type ContentMetricTile = {
  label: string;
  value: string;
};

type ContentSignalColumnProps = {
  queryChips: string[];
  metricTiles: ContentMetricTile[];
  signalRows: ContentSignalRow[];
};

export function ContentSignalColumn({
  queryChips,
  metricTiles,
  signalRows
}: ContentSignalColumnProps) {
  return (
    <ContentMapColumn
      icon={<Search aria-hidden="true" size={18} />}
      title="Sygnały i braki"
      subtitle="GSC, Ahrefs i brief"
    >
      <div className="space-y-3">
        <div className="rounded-md border border-line bg-white p-3">
          <div className="text-xs font-semibold text-slate-600">Kluczowe zapytania</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {queryChips.map((query) => (
              <span key={query} className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
                {query}
              </span>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {metricTiles.map((tile) => (
            <div key={tile.label} className="rounded-md border border-line bg-surface px-3 py-2">
              <div className="text-[11px] font-semibold uppercase tracking-normal text-slate-500">
                {tile.label}
              </div>
              <div className="mt-1 text-sm font-semibold text-ink">{tile.value}</div>
            </div>
          ))}
        </div>
        {signalRows.slice(0, 2).map((row) => (
          <div key={row.label} className={`rounded-md border p-3 ${row.tone}`}>
            <div className="text-xs font-semibold uppercase tracking-normal">{row.label}</div>
            <p className="mt-1 line-clamp-3 text-sm leading-6 text-slate-700">{row.summary}</p>
          </div>
        ))}
      </div>
    </ContentMapColumn>
  );
}
