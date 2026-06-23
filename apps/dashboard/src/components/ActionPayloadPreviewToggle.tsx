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
  const payloadKeys = Object.keys(payload);
  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Payload ActionObject
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            {intro} Klucze: {payloadKeys.slice(0, 5).join(", ") || "brak"}
            {payloadKeys.length > 5 ? ` +${payloadKeys.length - 5}` : ""}.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowPayload((current) => !current)}
          className="rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
        >
          {showPayload ? "Ukryj payload ActionObject" : "Pokaż payload ActionObject"}
        </button>
      </div>
      {showPayload ? (
        <pre
          className={`mt-3 ${maxHeightClass} overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100`}
        >
          {JSON.stringify(payload, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
