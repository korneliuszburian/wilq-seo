import { useQuery } from "@tanstack/react-query";
import { ClipboardCheck, Copy } from "lucide-react";

import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import { CommandCenterResponse, getCommandCenter } from "../lib/api";
import { marketerBlockedClaimLabels, priorityLabel } from "./marketingLabels";

function marketerConnectorLabels(values: string[]) {
  return Array.from(new Set(values.map(marketerConnectorLabel)));
}

function marketerConnectorLabel(value: string) {
  const labels: Record<string, string> = {
    ahrefs: "Ahrefs",
    facebook: "Facebook",
    google_ads: "Google Ads",
    google_analytics_4: "GA4",
    google_merchant_center: "Merchant Center",
    google_search_console: "Google Search Console",
    google_sheets: "Google Sheets",
    linkedin: "LinkedIn",
    localo: "Localo",
    wordpress_ekologus: "WordPress ekologus.pl",
    wordpress_sklep: "WordPress sklep.ekologus.pl"
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function codexSkillLabel(value: string) {
  const labels: Record<string, string> = {
    "wilq-ads-doctor": "Ads Doctor",
    "wilq-ahrefs-gap-finder": "Ahrefs Gap Finder",
    "wilq-campaign-builder": "Campaign Builder",
    "wilq-content-strategist": "Content Strategist",
    "wilq-custom-segments": "Custom Segments",
    "wilq-daily-command": "Daily Command",
    "wilq-demand-gen-operator": "Demand Gen Operator",
    "wilq-ga4-analyst": "GA4 Analyst",
    "wilq-gsc-content-doctor": "GSC Content Doctor",
    "wilq-localo-operator": "Localo Operator",
    "wilq-merchant-feed-operator": "Merchant Feed Operator",
    "wilq-social-publisher": "Social Publisher"
  };
  return labels[value] ?? value.replace(/^wilq-/, "").replaceAll("-", " ");
}

function evidenceCountSummary(count: number) {
  if (count === 0) return "brak potwierdzonych śladów w WILQ API";
  if (count === 1) return "1 potwierdzony ślad w WILQ API";
  return `${count} potwierdzonych śladów w WILQ API`;
}

function actionValidationSummary(count: number) {
  if (count === 0) return "brak bezpiecznej akcji na pierwszym ekranie";
  if (count === 1) return "1 bezpieczna akcja do walidacji";
  return `${count} bezpiecznych akcji do walidacji`;
}

function marketerDecisionText(value: string) {
  return value
    .replace(/`?act_[a-z0-9_]+`?/gi, "ActionObject w widoku szczegółowym")
    .replace(/`?ev_[a-z0-9_]+`?/gi, "dowód w WILQ API");
}

function DailyDecisionBoard({ data }: { data: CommandCenterResponse }) {
  return (
    <section>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dzisiejsze decyzje marketera
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {data.primary_next_step}
          </p>
        </div>
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        {data.daily_decisions.map((item) => (
          <article key={item.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  Decyzja / {priorityLabel(item.priority)}
                </div>
                <h3 className="mt-1 text-base font-semibold tracking-normal">{item.title}</h3>
              </div>
              <StatusBadge value={item.status} />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">
              {marketerDecisionText(item.co_widzimy)}
            </p>
            {Object.keys(item.metric_tiles ?? {}).length > 0 ? (
              <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-3">
                {Object.entries(item.metric_tiles).map(([label, value]) => (
                  <MetricTile key={label} label={label} value={value} />
                ))}
              </div>
            ) : null}
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {marketerDecisionText(item.dlaczego_to_ma_znaczenie)}
            </p>
            <p className="mt-2 text-sm font-medium text-ink">
              {marketerDecisionText(item.bezpieczny_next_step)}
            </p>
            {item.skill_id && item.codex_prompt ? (
              <div className="mt-3 rounded-md border border-action/25 bg-action/5 p-3 text-sm">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-action">
                  <Copy aria-hidden="true" size={15} />
                  Jak Codex może pomóc
                </div>
                <p className="mt-2 text-xs font-semibold uppercase tracking-normal text-slate-500">
                  Prompt do Codex
                </p>
                <p className="mt-2 leading-6 text-slate-700">{item.codex_prompt}</p>
                <div className="mt-2 text-xs text-slate-600">
                  Tryb Codexa: {codexSkillLabel(item.skill_id)}
                </div>
                {item.codex_context_endpoint ? (
                  <div className="mt-1 text-xs text-slate-600">
                    Kontekst: WILQ API i dowody tej decyzji
                  </div>
                ) : null}
                {item.expected_codex_output ? (
                  <p className="mt-2 leading-6 text-slate-700">
                    Oczekiwany wynik: {item.expected_codex_output}
                  </p>
                ) : null}
              </div>
            ) : null}
            <div className="mt-3 grid gap-2 text-xs text-slate-600">
              <TraceLine label="Źródła danych" values={marketerConnectorLabels(item.source_connectors)} />
              <TraceLine label="Dowody w API" values={[evidenceCountSummary(item.evidence_ids.length)]} />
              <TraceLine label="Akcje do walidacji" values={[actionValidationSummary(item.action_ids.length)]} />
              <TraceLine label="Czego nie twierdzimy" values={marketerBlockedClaimLabels(item.blocked_claims)} />
            </div>
            <a
              href={item.route}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-line px-3 text-sm font-medium text-ink hover:bg-slate-50"
            >
              Otwórz działanie
            </a>
          </article>
        ))}
      </div>
    </section>
  );
}

function SourceHealthSummary({ data }: { data: CommandCenterResponse }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Źródła i ograniczenia
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            To jest tylko skrót zdrowia źródeł. Pełne statusy connectorów, braki
            uprawnień i etykiety źródeł dostępu są w ustawieniach, nie w planie dnia.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Źródła" value={data.connector_summary.total} />
          <MetricTile label="Aktywne" value={data.connector_summary.configured} />
          <MetricTile label="Do naprawy" value={data.connector_summary.missing_credentials} />
        </div>
      </div>
      <a
        href="/settings"
        className="mt-4 inline-flex h-9 items-center rounded-md border border-line px-3 text-sm font-medium text-ink hover:bg-slate-50"
      >
        Otwórz ustawienia
      </a>
    </section>
  );
}

function ErrorState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <BlockerNotice message="WILQ API is not reachable." />
    </main>
  );
}

export function CommandCenter() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["command-center"],
    queryFn: getCommandCenter
  });

  if (isLoading) return <LoadingBand />;
  if (error || !data) return <ErrorState />;
  const sourceCount = Array.from(
    new Set(data.daily_decisions.flatMap((item) => item.source_connectors))
  ).length;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Command Center</h1>
          <p className="mt-1 text-sm text-slate-600">{data.strict_instruction}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={data.daily_decisions.length} />
          <MetricTile label="Blockery" value={data.blocker_count} />
          <MetricTile label="Źródła" value={sourceCount} />
        </div>
      </div>

      <div className="grid gap-8">
        <DailyDecisionBoard data={data} />

        <SourceHealthSummary data={data} />
      </div>
    </main>
  );
}
