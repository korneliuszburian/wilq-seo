import { useState } from "react";

export function ActionPayloadPreviewToggle({
  payload,
  intro,
  maxHeightClass = "max-h-56"
}: {
  payload: Record<string, unknown>;
  intro: string;
  maxHeightClass?: string;
}) {
  const [showPayload, setShowPayload] = useState(false);
  return (
    <div className="mt-3">
      <div>
        <button
          type="button"
          onClick={() => setShowPayload((current) => !current)}
          className="rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
        >
          {showPayload ? "Ukryj dane techniczne akcji" : "Pokaż dane techniczne akcji"}
        </button>
      </div>
      {showPayload ? (
        <div className="mt-3 rounded-md border border-line bg-slate-50 p-3">
          <p className="text-xs leading-5 text-slate-600">
            {intro} Szczegóły techniczne są schowane na wejściu; otwieraj je tylko przy
            sprawdzaniu zgodności albo audycie.
          </p>
          <pre
            className={`mt-3 ${maxHeightClass} overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100`}
          >
            {JSON.stringify(payload, null, 2)}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
