import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Boxes, ClipboardList, RefreshCw, ShoppingCart } from "lucide-react";

import { getActions, getMerchantDiagnostics } from "../lib/api";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import {
  MerchantExpandableActionsPanel,
  MerchantExpandableReviewPanel
} from "./MerchantSections/ReviewActionsSections";
import type { MerchantDecisionItem, MerchantDiagnosticsResponse } from "./MerchantSections/shared";
export function MerchantDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["merchant-diagnostics"],
    queryFn: getMerchantDiagnostics
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });
  if (diagnostics.isLoading || actions.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać danych Merchant. Ten widok nie może udawać wniosków o pliku produktowym bez WILQ." />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się pobrać akcji do sprawdzenia. Odśwież widok albo sprawdź status WILQ." />
      </main>
    );
  }
  const data = diagnostics.data;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <MerchantOperatingViewport data={data} />
      <MerchantExpandableReviewPanel data={data} />
      {routeActions.length > 0 ? (
        <div className="mt-6">
          <MerchantExpandableActionsPanel
            actions={routeActions}
            actionSummaryLabel={data.action_summary_label}
          />
        </div>
      ) : null}
    </main>
  );
}
function MerchantOperatingViewport({ data }: { data: MerchantDiagnosticsResponse }) {
  const primaryDecision = primaryMerchantDecision(data);
  const stale = data.freshness_assessment.requires_refresh;
  const criticalBlockedClaims = uniqueValues([
    ...data.operator_summary.blocked_claim_labels,
    ...(primaryDecision?.blocked_claim_labels ?? [])
  ]).slice(0, 4);
  return (
    <>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal text-ink">Produkty</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Merchant Center, plik produktowy i bezpieczna kolejka problemów produktów.
          </p>
        </div>
      </div>
      <MerchantMobileDecisionCard data={data} primaryDecision={primaryDecision} />
      <section className="mb-4 hidden gap-4 sm:grid md:grid-cols-2 xl:grid-cols-4">
        <MerchantStatCard
          icon={<ShoppingCart aria-hidden="true" size={22} />}
          value={data.product_count ?? 0}
          label="produktów w ostatnim odczycie"
          cta="Zobacz kolejkę"
          tone="blue"
        />
        <MerchantStatCard
          icon={<AlertTriangle aria-hidden="true" size={22} />}
          value={data.operator_summary.reported_issue_occurrences}
          label="problemów do sprawdzenia"
          cta="Wymagają przeglądu"
          tone="red"
        />
        <MerchantStatCard
          icon={<ClipboardList aria-hidden="true" size={22} />}
          value={data.decision_queue.length}
          label="decyzji produktowych"
          cta={data.action_summary_label}
          tone="amber"
        />
        <MerchantStatCard
          icon={<RefreshCw aria-hidden="true" size={22} />}
          value={stale ? `${Math.round(data.freshness_assessment.age_hours ?? 0)}h` : "OK"}
          label="świeżość danych"
          cta={data.freshness_assessment.state_label}
          tone={stale ? "purple" : "green"}
        />
      </section>
      {stale ? (
        <div className="hidden sm:block">
          <MerchantStaleDataBanner data={data} />
        </div>
      ) : null}
      <section className="mb-6 rounded-md border border-line bg-white px-4 py-3">
        <div className="grid gap-3 text-sm text-slate-700 md:grid-cols-4">
          <MerchantSourceStatus label="Merchant" value={data.connector_status_label} tone="green" />
          <MerchantSourceStatus
            label="Odczyt"
            value={data.latest_refresh_status_label ?? "brak ostatniego odczytu"}
            tone={stale ? "amber" : "green"}
          />
          <MerchantSourceStatus label="Dane" value={data.live_data_status_label} tone="green" />
          <MerchantSourceStatus
            label="Podstawa decyzji"
            value={marketerProofLabel(data.evidence_summary_label)}
            tone="blue"
          />
        </div>
      </section>
      <section className="mb-6 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <article className="rounded-md border border-line bg-white shadow-sm">
          <div className="flex min-h-12 items-center justify-between gap-3 border-b border-action/20 bg-blue-50 px-4 py-3">
            <h2 className="text-base font-semibold text-ink">Najważniejsza praca teraz</h2>
            <StatusBadge value={primaryDecision?.priority <= 20 ? "high" : "medium"} label={primaryDecision?.priority_label ?? "priorytet"} />
          </div>
          <div className="p-4">
            {primaryDecision ? (
              <div className="flex items-start gap-3">
                <div className="rounded-full bg-blue-100 p-3 text-action">
                  <Boxes aria-hidden="true" size={24} />
                </div>
                <div className="min-w-0">
                  <h3 className="text-lg font-semibold leading-6 text-ink">
                    {merchantDecisionMarketerTitle(primaryDecision)}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    {merchantDecisionMarketerSummary(primaryDecision)}
                  </p>
                  <div className="mt-4 grid gap-3 rounded-md border border-line bg-slate-50 p-3 md:grid-cols-2">
                    <MetricTile
                      label="Co sprawdzić"
                      value={merchantDecisionCheckLabel(primaryDecision)}
                    />
                    <MetricTile
                      label="Źródła"
                      value={marketerProofLabel(primaryDecision.evidence_summary_label)}
                    />
                  </div>
                  <h4 className="mt-4 text-sm font-semibold text-ink">Co teraz zrobić</h4>
                  <p className="mt-1 text-sm leading-6 text-slate-700">
                    {merchantDecisionMarketerNextStep(primaryDecision)}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <a
                      href={primaryDecision.action_ids[0] ? `/actions/${primaryDecision.action_ids[0]}` : "#merchant-queue"}
                      className="inline-flex h-10 items-center rounded-md bg-action px-4 text-sm font-semibold text-white hover:bg-blue-700"
                    >
                      Otwórz sprawdzenie
                    </a>
                    <a
                      href="#merchant-queue"
                      className="inline-flex h-10 items-center rounded-md border border-action/30 bg-white px-4 text-sm font-semibold text-action hover:bg-blue-50"
                    >
                      Pokaż problemy
                    </a>
                  </div>
                </div>
              </div>
            ) : (
              <BlockerNotice message="Brak decyzji Merchant w WILQ. Najpierw uruchom odczyt danych Merchant." />
            )}
          </div>
        </article>
        <article className="rounded-md border border-line bg-white shadow-sm">
          <div className="flex min-h-12 items-center justify-between gap-3 border-b border-risk/20 bg-red-50 px-4 py-3">
            <h2 className="text-base font-semibold text-ink">Co blokuje decyzję</h2>
            <StatusBadge value={stale ? "high" : "medium"} label={stale ? "odśwież najpierw" : "wymaga sprawdzenia"} />
          </div>
          <div className="divide-y divide-line">
            <MerchantBlockerRow
              title={stale ? "Dane Merchant są stare" : "Dane Merchant są gotowe do przeglądu"}
              detail={stale ? data.freshness_assessment.next_step : data.freshness_assessment.summary}
            />
            <MerchantBlockerRow
              title="WILQ nie zmienia pliku produktowego automatycznie"
              detail="Najpierw pokazuje problem i proponowany kierunek. Zapis wymaga osobnego przeglądu człowieka."
            />
            <MerchantBlockerRow
              title="Liczby pokazują skalę problemów"
              detail="Nie traktuj ich jako gotowej listy produktów do poprawki. Najpierw otwórz kolejkę i sprawdź typ problemu."
            />
          </div>
          <div className="p-4">
            <h3 className="text-sm font-semibold text-ink">Nie wolno dziś twierdzić</h3>
            <div className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
              {criticalBlockedClaims.map((claim) => (
                <span key={claim} className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-wait" />
                  {claim}
                </span>
              ))}
            </div>
          </div>
        </article>
      </section>
      <MerchantQueuePreview data={data} />
    </>
  );
}
function MerchantMobileDecisionCard({
  data,
  primaryDecision
}: {
  data: MerchantDiagnosticsResponse;
  primaryDecision: MerchantDecisionItem | undefined;
}) {
  const stale = data.freshness_assessment.requires_refresh;
  return (
    <section
      aria-label="Mobilna decyzja Merchant"
      className="mb-4 rounded-md border border-wait/40 bg-white p-4 shadow-sm sm:hidden"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-semibold uppercase tracking-normal text-action">Produkty</div>
        <span className="rounded-md bg-wait/10 px-2 py-1 text-xs font-semibold text-wait">
          {stale ? data.freshness_assessment.state_label : "do sprawdzenia"}
        </span>
      </div>
      <h2 className="mt-2 text-lg font-semibold leading-6 text-ink">
        {primaryDecision ? merchantDecisionMarketerTitle(primaryDecision) : "Najpierw sprawdź dane Merchant"}
      </h2>
      <p className="mt-2 line-clamp-3 text-sm leading-5 text-slate-700">
        {stale
          ? data.freshness_assessment.summary
          : primaryDecision
            ? merchantDecisionMarketerSummary(primaryDecision)
            : "WILQ nie ma potwierdzonej decyzji produktowej."}
      </p>
      <p className="mt-2 text-sm font-semibold leading-5 text-ink">
        {stale
          ? data.freshness_assessment.next_step
          : primaryDecision
            ? merchantDecisionMarketerNextStep(primaryDecision)
            : "Uruchom odczyt danych Merchant."}
      </p>
      <a
        href={stale ? "/settings" : primaryDecision?.action_ids[0] ? `/actions/${primaryDecision.action_ids[0]}` : "#merchant-queue"}
        className="mt-3 inline-flex h-10 w-full items-center justify-center rounded-md bg-action px-3 text-sm font-semibold text-white"
      >
        {stale ? "Odśwież w Źródłach" : "Otwórz sprawdzenie"}
      </a>
    </section>
  );
}
function MerchantStaleDataBanner({ data }: { data: MerchantDiagnosticsResponse }) {
  const ageLabel =
    typeof data.freshness_assessment.age_hours === "number"
      ? `${Math.round(data.freshness_assessment.age_hours)}h temu`
      : data.freshness_assessment.state_label;
  return (
    <section className="mb-6 rounded-md border border-wait/40 bg-wait/10 p-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <AlertTriangle aria-hidden="true" className="mt-1 shrink-0 text-wait" size={20} />
          <div>
            <h2 className="text-lg font-semibold text-ink">Najpierw odśwież dane Merchant</h2>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
              Ostatni odczyt ma {ageLabel}. Możesz zobaczyć problemy z tamtego odczytu,
              ale aktualną decyzję o pliku produktowym podejmuj dopiero po odświeżeniu danych.
            </p>
            <p className="mt-1 text-sm font-medium text-slate-700">
              {data.freshness_assessment.next_step}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href="/settings"
            className="inline-flex h-10 items-center rounded-md border border-wait/40 bg-white px-4 text-sm font-semibold text-wait hover:bg-amber-50"
          >
            Odśwież w Źródłach
          </a>
          <a
            href="#merchant-queue"
            className="inline-flex h-10 items-center rounded-md bg-wait px-4 text-sm font-semibold text-white hover:bg-amber-700"
          >
            Pokaż problemy z odczytu
          </a>
        </div>
      </div>
    </section>
  );
}
function MerchantStatCard({
  icon,
  value,
  label,
  cta,
  tone
}: {
  icon: React.ReactNode;
  value: number | string;
  label: string;
  cta: string;
  tone: "blue" | "green" | "amber" | "red" | "purple";
}) {
  const toneClass = {
    blue: "bg-blue-100 text-action",
    green: "bg-emerald-100 text-emerald-700",
    amber: "bg-amber-100 text-amber-700",
    red: "bg-red-100 text-risk",
    purple: "bg-violet-100 text-violet-700"
  }[tone];
  return (
    <article className="rounded-md border border-line bg-white p-4 shadow-sm">
      <div className="flex items-center gap-4">
        <div className={`rounded-full p-3 ${toneClass}`}>{icon}</div>
        <div>
          <div className="text-2xl font-semibold text-ink">{formatMerchantValue(value)}</div>
          <div className="text-sm text-slate-700">{label}</div>
        </div>
      </div>
      <div className="mt-3 text-sm font-medium text-action">{cta}</div>
    </article>
  );
}
function MerchantSourceStatus({
  label,
  value,
  tone
}: {
  label: string;
  value: string;
  tone: "blue" | "green" | "amber";
}) {
  const dotClass = tone === "green" ? "bg-emerald-500" : tone === "amber" ? "bg-wait" : "bg-action";
  return (
    <div className="flex items-center gap-2">
      <span className="font-semibold text-ink">{label}</span>
      <span className={`h-2 w-2 rounded-full ${dotClass}`} />
      <span>{value}</span>
    </div>
  );
}
function MerchantBlockerRow({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <AlertTriangle aria-hidden="true" className="mt-0.5 shrink-0 text-risk" size={16} />
      <div>
        <div className="text-sm font-semibold text-ink">{title}</div>
        <div className="mt-0.5 text-sm leading-5 text-slate-600">{detail}</div>
      </div>
    </div>
  );
}
function MerchantQueuePreview({ data }: { data: MerchantDiagnosticsResponse }) {
  const rows = data.decision_queue.slice(0, 6);
  if (rows.length === 0) {
    return (
      <section id="merchant-queue" className="mb-6 rounded-md border border-line bg-white p-4">
        <BlockerNotice message="Brak kolejki Merchant. Najpierw uruchom odczyt danych Merchant." />
      </section>
    );
  }
  return (
    <section id="merchant-queue" className="mb-6 overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="flex min-h-12 items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold text-ink">Kolejka problemów produktów</h2>
        <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
          {data.decision_queue.length} decyzji
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold text-slate-600">
            <tr>
              <th className="px-4 py-3">Priorytet</th>
              <th className="px-4 py-3">Problem</th>
              <th className="px-4 py-3">Podstawa decyzji</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Następny krok</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((decision) => (
              <tr key={decision.id} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-4 py-3">
                  <span className="rounded border border-risk/30 bg-risk/10 px-2 py-1 text-xs font-semibold text-risk">
                    {decision.priority_label}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-ink">{merchantDecisionMarketerTitle(decision)}</div>
                  <div className="mt-1 text-xs leading-5 text-slate-600">
                    {merchantDecisionShortContext(decision)}
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-700">
                  {marketerProofLabel(decision.evidence_summary_label)}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge value={decision.status} label={decision.status_label} />
                </td>
                <td className="px-4 py-3 text-slate-700">
                  {decision.action_ids[0] ? (
                    <a className="font-medium text-action hover:underline" href={`/actions/${decision.action_ids[0]}`}>
                      Przejdź do review
                    </a>
                  ) : (
                    decision.next_step
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
function primaryMerchantDecision(data: MerchantDiagnosticsResponse) {
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  return (
    data.operator_summary.top_decision_ids
      .map((decisionId) => decisionsById.get(decisionId))
      .find((decision): decision is MerchantDecisionItem => Boolean(decision)) ??
    data.decision_queue[0]
  );
}
function merchantDecisionShortContext(decision: MerchantDecisionItem) {
  return [
    decision.issue_type_label && !decision.title.includes(decision.issue_type_label)
      ? decision.issue_type_label
      : null,
    decision.affected_attribute_label ? `atrybut: ${decision.affected_attribute_label}` : null,
    decision.product_count ? `skala: ${decision.product_count}` : null,
    decision.sample_titles.length ? `${decision.sample_titles.length} przykłady w pełnym przeglądzie` : null
  ].filter((value): value is string => Boolean(value)).join(" · ");
}
function merchantDecisionMarketerTitle(decision: MerchantDecisionItem) {
  if (decision.id.includes("review_ads_product_state_mapping")) {
    return "Sprawdź, czy produkty z Merchant zgadzają się z Ads";
  }
  return merchantDecisionQueueTitle(decision);
}
function merchantDecisionMarketerSummary(decision: MerchantDecisionItem) {
  if (decision.id.includes("review_ads_product_state_mapping")) {
    return "WILQ znalazł próbki produktów, które warto porównać z Ads: status, dostępność i cenę. To kontrola spójności danych, nie ocena sprzedaży ani wyniku kampanii.";
  }
  return decision.summary;
}
function merchantDecisionMarketerNextStep(decision: MerchantDecisionItem) {
  if (decision.id.includes("review_ads_product_state_mapping")) {
    return "Otwórz sprawdzenie i porównaj status, dostępność oraz cenę. Nie zmieniaj pliku produktowego, dopóki świeży odczyt i review nie potwierdzą problemu.";
  }
  return decision.next_step;
}
function merchantDecisionCheckLabel(decision: MerchantDecisionItem) {
  if (decision.id.includes("review_ads_product_state_mapping")) {
    return "status, dostępność i cena w Ads";
  }
  return decision.issue_type_label ?? decision.decision_type_label;
}
function merchantDecisionQueueTitle(decision: MerchantDecisionItem) {
  return decision.title.replace(/^Merchant:\s*/i, "").replace(/\s+-\s+.+$/, "");
}
function formatMerchantValue(value: number | string) {
  if (typeof value === "number") {
    return new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 0 }).format(value);
  }
  return value;
}
function marketerProofLabel(label: string) {
  return label
    .replace(/\bdowody źródłowe\b/gi, "źródła")
    .replace(/\bdowód źródłowy\b/gi, "źródło");
}
function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
