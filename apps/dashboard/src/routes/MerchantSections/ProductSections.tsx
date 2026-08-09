import { ActionPreviewCard } from "../../components/ActionPreviewCard";
import { LabelChipRow, MetricTile } from "../../components/OperatorPrimitives";
import { StatusBadge } from "../../components/StatusBadge";
import { TraceLine } from "../../components/TraceLine";
import type {
  MerchantDecisionItem,
  MerchantDiagnosticsResponse,
  MerchantProductPerformanceRow
} from "./shared";

export function MerchantProductSampleReadiness({ data }: { data: MerchantDiagnosticsResponse }) {
  const readiness = data.product_sample_readiness;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Gotowość próbek produktów
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {readiness.summary}
          </p>
          <p className="mt-2 text-sm font-medium text-ink">
            {readiness.next_step}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs">
          <MetricTile label="Status" value={readiness.status_label} />
          <MetricTile label="Próbki" value={readiness.sample_count} />
        </div>
      </div>
      <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine label="Stan danych" values={[readiness.summary, readiness.next_step]} />
        <TraceLine
          label="Przykładowe produkty"
          values={[
            readiness.sample_summary_label ||
              "WILQ nie podał próbek produktów; sprawdź Merchant przed edycją"
          ]}
        />
        <TraceLine
          label="Przykładowe tytuły"
          values={
            readiness.sample_title_labels.length
              ? readiness.sample_title_labels
              : ["WILQ nie podał tytułów próbek; identyfikuj produkt w Merchant przed oceną"]
          }
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={readiness.blocked_claim_labels}
        />
      </div>
    </section>
  );
}

export function MerchantProductPerformanceReadiness({ data }: { data: MerchantDiagnosticsResponse }) {
  const readiness = data.product_performance_readiness;
  const visibleRows = readiness.performance_rows.slice(0, 4);
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Produkty połączone z Ads/GA4
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {readiness.summary}
          </p>
          <p className="mt-2 text-sm font-medium text-ink">
            {readiness.next_step}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Status" value={readiness.status_label} />
          <MetricTile label="Połączone produkty" value={readiness.joined_product_count} />
          <MetricTile label="Próbki" value={readiness.merchant_sample_count} />
        </div>
      </div>
      <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine label="Stan danych" values={[readiness.summary, readiness.next_step]} />
        <TraceLine
          label="Źródła"
          values={readiness.source_connector_labels}
          empty="WILQ nie podał źródeł danych; nie łącz Merchant z Ads/GA4 bez odczytu."
        />
        <TraceLine
          label="Dowody"
          values={readiness.evidence_summary_label ? [readiness.evidence_summary_label] : []}
          empty="WILQ nie podał dowodów źródłowych; nie oceniaj gotowości połączenia."
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={readiness.blocked_claim_labels}
        />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
        <MetricTile label="Fakty Ads" value={readiness.ads_product_fact_count} />
        <MetricTile label="Fakty GA4" value={readiness.ga4_product_fact_count} />
        <MetricTile label="Próbki produktów" value={readiness.sample_product_summary_label} />
        <MetricTile label="Wiersze" value={readiness.performance_rows.length} />
      </div>
      {visibleRows.length > 0 ? (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {visibleRows.map((row) => (
            <MerchantProductPerformanceRowCard key={row.product_id} row={row} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

function MerchantProductPerformanceRowCard({
  row
}: {
  row: MerchantProductPerformanceRow;
}) {
  const title = row.title_label || "Produkt Merchant do sprawdzenia";
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-1 text-xs text-slate-500">{row.product_reference_label}</p>
      <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs">
        <MetricTile label="Status Ads" value={row.ads_product_status_label} />
        <MetricTile label="Dostępność Ads" value={row.ads_product_availability_label} />
        <MetricTile label="Cena Ads" value={row.ads_product_price_label} />
        <MetricTile label="Kliknięcia Ads" value={row.ads_clicks_label} />
        <MetricTile label="Koszt Ads" value={row.ads_cost_label} />
        <MetricTile label="Zakupy GA4" value={row.ga4_ecommerce_purchases_label} />
        <MetricTile label="Przychód GA4" value={row.ga4_purchase_revenue_label} />
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Problem Merchant"
          values={[
            row.issue_type_label,
            row.affected_attribute_label,
            row.country,
            row.reporting_context_label
          ].filter((value): value is string => Boolean(value))}
          empty="WILQ nie podał kontekstu problemu; nie edytuj produktu bez sprawdzenia."
        />
        <TraceLine
          label="Źródła"
          values={row.source_connector_labels}
          empty="WILQ nie podał źródeł danych; nie oceniaj wiersza bez odczytu Merchant."
        />
        <TraceLine
          label="Dowody"
          values={row.evidence_summary_label ? [row.evidence_summary_label] : []}
          empty="WILQ nie podał dowodów źródłowych; nie traktuj wiersza jako rekomendacji."
        />
        <TraceLine
          label="Brakujące metryki"
          values={row.missing_metric_labels}
          empty="metryki kompletne"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={row.blocked_claim_labels}
        />
      </div>
    </article>
  );
}

export function MerchantPriceImpactReadiness({ data }: { data: MerchantDiagnosticsResponse }) {
  const readiness = data.price_impact_readiness;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Wpływ ceny produktu
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {readiness.summary}
          </p>
          <p className="mt-2 text-sm font-medium text-ink">{readiness.next_step}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-5">
          <MetricTile label="Status" value={readiness.status_label} />
          <MetricTile label="Ceny teraz" value={readiness.products_with_current_price} />
          <MetricTile label="Historia cen" value={readiness.products_with_previous_price} />
          <MetricTile label="Zmiany ceny" value={readiness.products_with_price_change} />
          <MetricTile
            label="Bez zmiany"
            value={readiness.products_with_unchanged_price_history}
          />
        </div>
      </div>
      <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine label="Stan danych" values={[readiness.summary, readiness.next_step]} />
        <TraceLine
          label="Źródła"
          values={readiness.source_connector_labels}
          empty="WILQ nie podał źródeł danych; nie oceniaj wpływu ceny bez odczytu."
        />
        <TraceLine
          label="Dowody"
          values={readiness.evidence_summary_label ? [readiness.evidence_summary_label] : []}
          empty="WILQ nie podał dowodów źródłowych; nie oceniaj wpływu ceny jako pewnego."
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={readiness.blocked_claim_labels}
        />
      </div>
      {readiness.preview_cards.length > 0 ? (
        <div className="mt-3 grid gap-2">
          {readiness.preview_cards.map((card) => (
            <ActionPreviewCard key={card.id} card={card} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function MerchantDecisionCard({ decision }: { decision: MerchantDecisionItem }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{decision.title}</h3>
          <LabelChipRow
            className="mt-1"
            chips={[
              { label: "Typ", value: decision.decision_type_label },
              { label: "Priorytet", value: decision.priority_label }
            ]}
          />
        </div>
        <StatusBadge value={decision.risk} label={decision.risk_label} />
      </div>
      {decision.summary ? (
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {decision.summary}
        </p>
      ) : null}
      <p className="mt-2 text-sm leading-6 text-slate-700">
        {decision.rationale}
      </p>
      <p className="mt-2 text-sm font-medium text-ink">
        {decision.next_step}
      </p>
      {Object.keys(decision.metric_tiles ?? {}).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
        {decision.issue_type ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            problem: {decision.issue_type_label ?? "problem pliku produktowego"}
          </span>
        ) : null}
        {decision.affected_attribute ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            atrybut: {decision.affected_attribute_label ?? "atrybut"}
          </span>
        ) : null}
        {decision.country ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            kraj: {decision.country}
          </span>
        ) : null}
        {decision.reporting_context_label ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            kontekst: {decision.reporting_context_label}
          </span>
        ) : null}
      </div>
      <div className="mt-2 grid gap-1.5 text-xs text-slate-600">
        {decision.sample_product_ids.length || decision.sample_titles.length ? (
          <div className="rounded border border-line bg-white p-2">
            <p className="font-medium text-ink">Przykładowe produkty do sprawdzenia</p>
            <TraceLine label="Próbki" values={["przykłady dostępne w pełnym przeglądzie"]} />
            <TraceLine
              label="Tytuły"
              values={decision.sample_titles.slice(0, 4)}
              empty="WILQ nie podał tytułów próbek; identyfikuj produkt w Merchant przed oceną."
            />
            <p className="mt-1 text-xs text-slate-500">
              To są przykłady z odczytu Merchant, nie pełna lista SKU ani gotowa zmiana pliku produktowego.
            </p>
          </div>
        ) : null}
        {decision.preview_cards.length > 0 ? (
          <div className="grid gap-2">
            {decision.preview_cards.map((card) => (
              <ActionPreviewCard key={card.id} card={card} />
            ))}
          </div>
        ) : null}
        <TraceLine
          label="Dowody"
          values={decision.evidence_summary_label ? [decision.evidence_summary_label] : []}
          empty="WILQ nie podał dowodów źródłowych; nie traktuj tej decyzji jako rekomendacji."
        />
        <TraceLine
          label="Akcje"
          values={[decision.action_summary_label]}
          empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczny przegląd."
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={decision.blocked_claim_labels}
        />
      </div>
    </article>
  );
}
