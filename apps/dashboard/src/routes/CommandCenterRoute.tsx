import { useQuery } from "@tanstack/react-query";
import { ClipboardCheck, Copy } from "lucide-react";

import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import { CommandCenterResponse, getCommandCenter } from "../lib/api";
import { marketerBlockedClaimLabels, priorityLabel } from "./marketingLabels";
import type { DailyDecision } from "@wilq/shared-schemas";

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
    "wilq-ads-doctor": "diagnostyka Ads",
    "wilq-ahrefs-gap-finder": "luki SEO Ahrefs",
    "wilq-campaign-builder": "plan kampanii",
    "wilq-content-strategist": "strategia treści",
    "wilq-custom-segments": "segmenty Ads",
    "wilq-daily-command": "plan dnia",
    "wilq-demand-gen-operator": "Demand Gen",
    "wilq-ga4-analyst": "analiza GA4",
    "wilq-gsc-content-doctor": "GSC i treści",
    "wilq-localo-operator": "widoczność lokalna",
    "wilq-merchant-feed-operator": "feed Merchant",
    "wilq-social-publisher": "treści social"
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

function marketerMetricLabel(label: string) {
  const labels: Record<string, string> = {
    "Ahrefs review": "ocena Ahrefs",
    "WP match": "dopasowania WP",
    "braki kontraktu": "braki danych",
    "jakość ruchu": "jakość ruchu",
    "link gaps": "luki linków",
    "podgląd budżetu": "budżety do oceny",
    "rekordy Ahrefs": "rekordy Ahrefs",
    "typy problemów": "typy problemów",
    "wartość konw.": "wartość konwersji",
    query: "zapytania",
    "query/page": "zapytania/URL"
  };
  return labels[label] ?? label;
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("pl-PL", {
    maximumFractionDigits: 2
  }).format(value);
}

function copyPromptToClipboard(prompt: string) {
  if (!navigator.clipboard) return;
  void navigator.clipboard.writeText(prompt);
}

type DecisionCopy = {
  title: string;
  what: string;
  why: string;
  nextStep: string;
};

function metricValue(item: DailyDecision, key: string): string | number | undefined {
  return item.metric_tiles?.[key];
}

function metricNumber(item: DailyDecision, key: string): number {
  const value = metricValue(item, key);
  if (typeof value === "number") return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return 0;
}

function metricDisplay(item: DailyDecision, key: string, fallback = "brak danych") {
  const value = metricValue(item, key);
  if (typeof value === "number") return formatNumber(value);
  if (typeof value === "string" && value.length > 0) return value;
  return fallback;
}

function sourceList(item: DailyDecision) {
  return marketerConnectorLabels(item.source_connectors).join(", ");
}

function decisionCopy(item: DailyDecision): DecisionCopy {
  if (item.id === "decision_review_merchant_feed_issues") {
    const products = metricDisplay(item, "produkty");
    const issueTypes = metricValue(item, "typy problemów");
    const issueTypePhrase =
      issueTypes === undefined ? "bez rozbicia na typy problemów" : `w ${issueTypes} typach`;
    const reports = metricDisplay(item, "zgłoszenia", metricDisplay(item, "issues"));
    return {
      title: "Przejrzyj problemy produktów w Merchant Center",
      what: `WILQ widzi ${products} produktów i ${reports} zgłoszeń problemów feedu ${issueTypePhrase}.`,
      why:
        "To może ograniczać widoczność produktów w Shopping i PMax, ale nie oznacza automatycznej naprawy ani odzyskanego przychodu.",
      nextStep:
        "Otwórz widok Merchant, sprawdź kolejkę problemów i waliduj akcję WILQ przed jakąkolwiek zmianą feedu."
    };
  }

  if (item.id === "decision_prepare_content_refresh_queue") {
    const queryPages = metricDisplay(item, "query/page");
    const clicks = metricDisplay(item, "kliknięcia");
    const impressions = metricDisplay(item, "wyświetlenia");
    const wpMatches = metricDisplay(item, "WP match");
    const ahrefsGaps = metricDisplay(item, "luki Ahrefs");
    const linkGaps = metricDisplay(item, "link gaps");
    const matchWarning =
      metricNumber(item, "WP match") === 0
        ? " Najpierw sprawdź mapowanie WordPress, bo API nie potwierdza dopasowania części adresów."
        : "";
    return {
      title: "Ułóż kolejkę odświeżenia i scalania treści SEO",
      what: `WILQ ma ${queryPages} par zapytanie-URL z GSC, ${clicks} kliknięć i ${impressions} wyświetleń. WordPress potwierdza ${wpMatches} dopasowań, a Ahrefs wskazuje ${ahrefsGaps} luki treści i ${linkGaps} luk linków.${matchWarning}`,
      why:
        "To jest materiał do decyzji refresh, merge, create albo block. Nie jest to obietnica wzrostu pozycji, leadów ani przychodu.",
      nextStep:
        "Otwórz Content Planner, zacznij od stron z największym ruchem z GSC i wybierz jedną decyzję dla każdego klastra."
    };
  }

  if (item.id === "decision_review_ga4_landing_quality") {
    const groups = metricDisplay(item, "grupy ruchu");
    const measurementIssues = metricDisplay(item, "pomiar");
    const qualitySignals = metricDisplay(item, "jakość ruchu");
    const contractGaps = metricDisplay(item, "braki kontraktu");
    return {
      title: "Sprawdź pomiar GA4 zanim ocenimy kampanie",
      what: `GA4 pokazuje ${groups} grup ruchu, ${measurementIssues} problemy pomiaru, ${qualitySignals} sygnały jakości ruchu i ${contractGaps} brak danych wymaganych do pełnej oceny.`,
      why:
        "Dopóki pomiar jest niepełny, WILQ blokuje wnioski o ROAS, przychodzie i spadkach konwersji. To jest kontrola jakości danych, nie werdykt o skuteczności kampanii.",
      nextStep:
        "Otwórz GA4, sprawdź strony wejścia, źródła ruchu i konfigurację zdarzeń. Najpierw naprawiamy pomiar, dopiero potem oceniamy wyniki."
    };
  }

  if (item.id === "decision_review_ads_campaign_metrics") {
    const campaigns = metricDisplay(item, "kampanie");
    const searchTerms = metricDisplay(item, "zapytania");
    const clicks = metricDisplay(item, "kliknięcia");
    const impressions = metricDisplay(item, "wyświetlenia");
    const cost = metricDisplay(item, "koszt");
    const conversions = metricDisplay(item, "konwersje");
    const conversionValue = metricDisplay(item, "wartość konw.");
    const negativeTerms = metricDisplay(item, "wykluczenia");
    const segments = metricDisplay(item, "segmenty");
    return {
      title: "Przejrzyj kampanie i wyszukiwane hasła w Google Ads",
      what: `Google Ads ma świeży odczyt: ${campaigns} kampanii, ${searchTerms} wyszukiwanych haseł, ${clicks} kliknięć, ${impressions} wyświetleń, koszt ${cost}, ${conversions} konwersje i wartość konwersji ${conversionValue}. WILQ przygotowuje też ${negativeTerms} terminów do oceny oraz ${segments} kandydatów segmentów.`,
      why:
        "To wystarcza do przeglądu kampanii i wyszukiwanych haseł, ale nie wystarcza jeszcze do automatycznego wykluczania fraz, zmiany budżetów ani werdyktu o opłacalności.",
      nextStep:
        "Otwórz Ads Doctor i przejrzyj metryki kampanii oraz wyszukiwane hasła. Każde wykluczenie, budżet i rekomendacja musi przejść przez akcję WILQ."
    };
  }

  return {
    title: item.title,
    what: `WILQ ma decyzję z obszaru: ${sourceList(item)}.`,
    why:
      "Ten element wymaga dedykowanego widoku szczegółowego, żeby nie zgadywać wniosków na pierwszym ekranie.",
    nextStep: "Otwórz wskazany widok i sprawdź szczegóły wraz z dowodami w WILQ API."
  };
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
        {data.daily_decisions.map((item) => {
          const copy = decisionCopy(item);
          return (
          <article key={item.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  Decyzja / {priorityLabel(item.priority)}
                </div>
                <h3 className="mt-1 text-base font-semibold tracking-normal">
                  {copy.title}
                </h3>
              </div>
              <StatusBadge value={item.status} />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">
              {copy.what}
            </p>
            {Object.keys(item.metric_tiles ?? {}).length > 0 ? (
              <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-3">
                {Object.entries(item.metric_tiles).map(([label, value]) => (
                  <MetricTile key={label} label={marketerMetricLabel(label)} value={value} />
                ))}
              </div>
            ) : null}
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {copy.why}
            </p>
            <p className="mt-2 text-sm font-medium text-ink">
              {copy.nextStep}
            </p>
            {item.skill_id && item.codex_prompt ? (
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-action/25 bg-action/5 p-3 text-sm">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-action">
                  <Copy aria-hidden="true" size={15} />
                  Codex: {codexSkillLabel(item.skill_id)}
                </div>
                <button
                  type="button"
                  onClick={() => copyPromptToClipboard(item.codex_prompt ?? "")}
                  className="inline-flex h-8 items-center rounded-md border border-action/30 px-3 text-xs font-semibold uppercase tracking-normal text-action hover:bg-action/10"
                >
                  Kopiuj prompt
                </button>
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
          );
        })}
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
