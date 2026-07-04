import { useQuery } from "@tanstack/react-query";
import { History, ShieldAlert } from "lucide-react";

import {
  getSocialPublisherContextPack,
  type SocialDraftContext,
  type SocialHistoryInventory
} from "../lib/api";
import {
  BlockerNotice,
  LabelChipRow,
  LoadingBand,
  MetricTile
} from "../components/OperatorPrimitives";
import { TraceLine } from "../components/TraceLine";
import { ActionFocus } from "./ActionPanels";

const FIELD_LABELS: Record<string, string> = {
  channel: "Kanał",
  published_at: "Data publikacji",
  topic: "Temat",
  service: "Usługa",
  claim: "Claim",
  cta: "CTA",
  format: "Format",
  post_url_or_id: "URL albo ID posta",
  source_evidence_id: "Dowód źródłowy"
};

export function SocialPublisherSurface() {
  const contextPack = useQuery({
    queryKey: ["social-publisher-context-pack"],
    queryFn: getSocialPublisherContextPack
  });

  if (contextPack.isLoading) return <LoadingBand />;
  if (contextPack.error || !contextPack.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się pobrać social context-packa. WILQ nie może pokazać szkiców ani blokad bez API." />
      </main>
    );
  }

  const socialContext = contextPack.data.social_draft_context;
  const inventory = socialContext.social_history_inventory;
  const actions = contextPack.data.active_action_objects.filter((action) =>
    socialContext.draft_action_ids.includes(action.id)
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Publikacje social</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ może przygotować tylko kierunki postów do sprawdzenia. Publikacja i
            claim o braku powtórek są zablokowane, dopóki nie ma dostępu oraz historii
            postów LinkedIn/Facebook.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Tryb" value={socialContext.mode === "review_only" ? "review" : socialContext.mode} />
          <MetricTile label="Publikacja" value={socialContext.publish_allowed ? "dostępna" : "zablokowana"} />
          <MetricTile label="Historia" value={inventory.status_label} />
        </div>
      </div>

      <div className="grid gap-6">
        <SocialDecisionSummary socialContext={socialContext} inventory={inventory} />
        <SocialHistoryBlocker inventory={inventory} socialContext={socialContext} />
        <ActionFocus actions={actions} />
      </div>
    </main>
  );
}

function SocialDecisionSummary({
  socialContext,
  inventory
}: {
  socialContext: SocialDraftContext;
  inventory: SocialHistoryInventory;
}) {
  return (
    <section className="rounded-md border border-wait/30 bg-wait/10 p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-wait/30 bg-white p-2 text-wait">
          <ShieldAlert aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-wait">
            Social jest tylko do review
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-700">
            {socialContext.operator_next_step}
          </p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <MetricTile label="Blokady twierdzeń" value={socialContext.blocked_claims.length} />
        <MetricTile label="Wymagane źródła historii" value={inventory.required_sources.length} />
        <MetricTile label="Akcje review-only" value={socialContext.draft_action_ids.length} />
      </div>
      <div className="mt-4 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Czego nie wolno twierdzić"
          values={socialContext.blocked_claims.slice(0, 6)}
          empty="Brak blokad twierdzeń oznaczałby brak bezpiecznego zakresu social."
        />
        <TraceLine
          label="Brakujące dowody historii"
          values={socialContext.missing_history_evidence}
          empty="Historia social nie wymaga dodatkowych dowodów."
        />
      </div>
    </section>
  );
}

function SocialHistoryBlocker({
  inventory,
  socialContext
}: {
  inventory: SocialHistoryInventory;
  socialContext: SocialDraftContext;
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
                {formatAccessStatus(source.connector_access_status)}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              Wymagany tylko spis metadanych. Pełna treść posta nie jest wymagana.
            </p>
            <LabelChipRow
              className="mt-3"
              chips={[
                { label: "Spis", value: formatInventoryStatus(source.inventory_status) },
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
              ? formatMetadataSourceStatus(inventory.metadata_source_status)
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

function formatAccessStatus(status: string) {
  if (status === "missing_credentials") return "brakuje dostępu";
  if (status === "configured") return "dostęp skonfigurowany";
  return "niedostępne";
}

function formatInventoryStatus(status: string) {
  if (status === "review_ready") return "gotowy do oceny";
  return "brak";
}

function formatMetadataSourceStatus(status: string) {
  if (status === "review_ready") return "poprawne metadane";
  if (status === "invalid") return "wymaga poprawy";
  return "niepodpięte";
}
