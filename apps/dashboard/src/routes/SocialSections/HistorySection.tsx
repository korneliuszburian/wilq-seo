import { History } from "lucide-react";

import type { SocialDraftContext, SocialHistoryInventory } from "../../lib/api";
import { LabelChipRow } from "../../components/OperatorPrimitives";
import { TraceLine } from "../../components/TraceLine";
import { FIELD_LABELS, type SocialHistoryStatusFormatters } from "./Shared";

export function SocialHistoryBlocker({
  inventory,
  socialContext,
  statusFormatters
}: {
  inventory: SocialHistoryInventory;
  socialContext: SocialDraftContext;
  statusFormatters: SocialHistoryStatusFormatters;
}) {
  const metadataFields = inventory.sources[0]?.required_metadata_fields ?? [];

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <History aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Historia social blokuje brak powtórek
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {inventory.operator_next_step}
          </p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {inventory.sources.map((source) => (
          <article key={source.channel} className="rounded-md border border-line bg-slate-50 p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="text-sm font-semibold capitalize">{source.channel}</h3>
              <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
                {statusFormatters.access(source.connector_access_status)}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              Wymagany tylko spis metadanych. Pełna treść posta nie jest wymagana.
            </p>
            <LabelChipRow
              className="mt-3"
              chips={[
                { label: "Spis", value: statusFormatters.inventory(source.inventory_status) },
                { label: "Tryb", value: source.safe_collection_mode },
                {
                  label: "Raw treść",
                  value: source.raw_post_body_allowed ? "dozwolona" : "niewymagana"
                }
              ]}
            />
          </article>
        ))}
      </div>
      <LabelChipRow
        className="mt-4"
        chips={[
          { label: "Status spisu", value: inventory.status_label },
          { label: "Pozycji", value: String(inventory.item_count) },
          {
            label: "Lokalne źródło",
            value: inventory.metadata_source_configured
              ? statusFormatters.metadataSource(inventory.metadata_source_status)
              : "niepodpięte"
          }
        ]}
      />
      {inventory.import_errors.length > 0 ? (
        <div className="mt-4 rounded-md border border-danger/30 bg-danger/10 p-3">
          <h3 className="text-sm font-semibold text-danger">Co poprawić w spisie</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700">
            {inventory.import_errors.slice(0, 5).map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="mt-4 rounded-md border border-line bg-slate-50 p-3">
        <h3 className="text-sm font-semibold text-ink">Jakie pola trzeba zebrać</h3>
        <div className="mt-3 flex flex-wrap gap-2">
          {metadataFields.map((field) => (
            <span
              key={field}
              className="rounded-md border border-line bg-white px-2.5 py-1 text-xs text-slate-700"
            >
              {FIELD_LABELS[field] ?? field}
            </span>
          ))}
        </div>
      </div>
      <div className="mt-4 rounded-md border border-line bg-white p-3">
        <h3 className="text-sm font-semibold text-ink">Jak sprawdzić zebrane metadane</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Wyślij metadata-only JSON do WILQ API. Audit sprawdzi kompletność LinkedIn/Facebook
          i odrzuci raw treść, komentarze, dane użytkowników oraz tokeny. Wynik nadal jest
          tylko do review: nie odblokowuje publikacji ani claimu o braku powtórek.
        </p>
        <LabelChipRow
          className="mt-3"
          chips={[
            { label: "Endpoint", value: socialContext.history_audit_endpoint },
            { label: "Kontrakt", value: socialContext.history_audit_contract },
            { label: "Efekt", value: "review metadanych" }
          ]}
        />
      </div>
      <div className="mt-4 rounded-md border border-line bg-slate-50 p-3">
        <h3 className="text-sm font-semibold text-ink">Gotowy szablon metadanych</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {inventory.input_template._instruction}
        </p>
        <LabelChipRow
          className="mt-3"
          chips={[
            { label: "Data zebrania", value: inventory.input_template.collected_at },
            { label: "Reviewer", value: inventory.input_template.reviewer },
            {
              label: "Kanały w szablonie",
              value: inventory.input_template.items.map((item) => item.channel).join(", ")
            }
          ]}
        />
      </div>
      {inventory.discovery_seeds.length > 0 ? (
        <div className="mt-4 rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Od czego zacząć discovery</h3>
          <div className="mt-3 grid gap-2">
            {inventory.discovery_seeds.map((seed) => (
              <article key={seed.id} className="rounded-md border border-line bg-white p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold capitalize">{seed.channel}</span>
                  <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                    {seed.safe_collection_mode}
                  </span>
                </div>
                <a
                  className="mt-2 block break-all text-sm text-action underline-offset-2 hover:underline"
                  href={seed.source_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  {seed.source_url}
                </a>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {seed.operator_note}
                </p>
              </article>
            ))}
          </div>
        </div>
      ) : null}
      <div className="mt-4 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Dozwolone użycie"
          values={inventory.allowed_uses}
          empty="WILQ nie podał dozwolonego użycia historii social."
        />
        <TraceLine
          label="Zablokowane użycie"
          values={inventory.blocked_uses}
          empty="WILQ nie podał blokad historii social."
        />
      </div>
    </section>
  );
}
