import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpenCheck,
  FileText,
  ListChecks,
  SearchCheck,
  ShieldAlert,
  TrendingUp
} from "lucide-react";

import {
  ActionObject,
  ContentDiagnosticsResponse,
  ContentPreflightResponse,
  WordPressAuthoringProfile,
  getActions,
  getContentDiagnostics,
  getContentPreflight,
  getWordPressAuthoringProfile,
} from "../lib/api";
import { ActionPreviewCard } from "../components/ActionPreviewCard";
import { formatContentMetricValue } from "../lib/contentLabels";
import {
  BlockerNotice,
  LabelChipRow,
  LoadingBand,
  MetricTile,
} from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import {
  ActionLifecycleStrip,
  BlockerPanel,
  CompactStatTile,
  DashboardToolbar,
  DenseQueueTable,
  RiskPill,
  SourceFreshnessStrip,
  StatusPill
} from "../components/DashboardMockupPrimitives";
import {
  ActionFocus,
  ActionIdFocus,
} from "./ActionPanels";
import { shortPath } from "./TacticalQueuePanel";

type ContentDecisionItem = ContentDiagnosticsResponse["decision_queue"][number];
type ContentMetricFact = ContentDiagnosticsResponse["sections"][number]["metric_facts"][number];
type ContentPreflightItem = ContentPreflightResponse["items"][number];

export function ContentDiagnosticSurface({ title }: { title: string }) {
  const diagnostics = useQuery({
    queryKey: ["content-diagnostics"],
    queryFn: getContentDiagnostics
  });
  const preflight = useQuery({
    queryKey: ["content-preflight"],
    queryFn: getContentPreflight
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions,
    enabled: diagnostics.isSuccess
  });
  const authoringProfile = useQuery({
    queryKey: ["content-wordpress-authoring-profile"],
    queryFn: getWordPressAuthoringProfile,
    enabled: diagnostics.isSuccess
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać danych treści. Widok Content nie może udawać wniosków SEO bez danych źródłowych." />
      </main>
    );
  }

  const data = diagnostics.data;
  const routeActions = (actions.data ?? []).filter((action) => data.action_ids.includes(action.id));

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <ContentPlannerMockupViewport
        title={title}
        data={data}
        preflight={preflight.data}
        authoringProfile={authoringProfile.data}
      />

      <ContentPreflightPanel data={preflight.data} isLoading={preflight.isLoading} isError={Boolean(preflight.error)} />

      <ContentExpandableBriefPanel actions={routeActions} />

      <ContentExpandableReviewPanel data={data} />

      <ContentExpandableActionsPanel
        actions={routeActions}
        actionIds={data.action_ids}
        actionSummaryLabel={data.action_summary_label}
        isLoading={actions.isLoading}
        isError={Boolean(actions.error)}
      />
    </main>
  );
}

function ContentPlannerMockupViewport({
  title,
  data,
  preflight,
  authoringProfile
}: {
  title: string;
  data: ContentDiagnosticsResponse;
  preflight: ContentPreflightResponse | undefined;
  authoringProfile: WordPressAuthoringProfile | undefined;
}) {
  const selectedDecision = contentSelectedPrimaryDecision(data);
  const primaryPreflight = preflight?.primary_item ?? undefined;
  const rows = contentQueueRows(data);

  return (
    <div className="mb-6 grid gap-5">
      <DashboardToolbar
        title={title}
        description="Widok pracy nad treściami: konkretna strona, obecne sekcje WordPress, query z GSC, pomocnicze tropy Ahrefs i następny krok na devie."
        dateLabel="Dzisiaj"
        refreshLabel="Odśwież dane"
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {contentPlannerStatTiles(data, primaryPreflight).map((tile) => (
          <CompactStatTile
            key={tile.label}
            value={tile.value}
            label={tile.label}
            actionLabel={tile.actionLabel}
            tone={tile.tone}
            icon={tile.icon}
          />
        ))}
      </div>

      <SourceFreshnessStrip items={contentSourceFreshnessItems(data)} />

      <div className="grid gap-5 xl:grid-cols-[1fr_0.95fr]">
        <ContentNearestDecisionCard decision={selectedDecision} preflight={primaryPreflight} />
        <ContentDevWorkspacePanel authoringProfile={authoringProfile} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_0.95fr]">
        <ContentCurrentSectionsPanel decision={selectedDecision} />
        <BlockerPanel
          title="Czego dziś nie obiecujemy"
          badgeLabel="review required"
          items={contentBlockerPanelItems(data, primaryPreflight)}
        />
      </div>

      <DenseQueueTable
        title="Pozostałe treści i tropy"
        rows={rows}
        getRowKey={(row) => row.id}
        selectedRowKey={selectedDecision?.id}
        columns={[
          {
            key: "topic",
            header: "Temat",
            render: (row) => (
              <div className="min-w-64">
                <div className="font-semibold text-ink">{row.title}</div>
                <div className="mt-1 text-xs leading-5 text-slate-500">{row.detail}</div>
              </div>
            )
          },
          {
            key: "mode",
            header: "Decyzja",
            render: (row) => <StatusPill label={row.modeLabel} tone={row.modeTone} />
          },
          {
            key: "signals",
            header: "Sygnały",
            render: (row) => (
              <div className="grid gap-1 text-xs leading-5 text-slate-600">
                {row.signals.map((signal) => (
                  <span key={`${row.id}:${signal}`}>{signal}</span>
                ))}
              </div>
            )
          },
          {
            key: "gate",
            header: "Brama",
            render: (row) => <RiskPill label={row.gateLabel} risk={row.risk} />
          },
          {
            key: "next",
            header: "Następny krok",
            render: (row) => (
              <span className="text-sm font-medium leading-5 text-action">{row.nextStep}</span>
            )
          }
        ]}
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_0.9fr]">
        <ActionLifecycleStrip
          steps={[
            { label: "Dane", state: data.live_data_available ? "done" : "blocked" },
            { label: "Preflight", state: primaryPreflight ? "current" : "waiting" },
            {
              label: "Plan",
              state: primaryPreflight?.sales_brief_allowed ? "current" : "waiting"
            },
            {
              label: "Review",
              state: primaryPreflight?.draft_allowed || primaryPreflight?.wordpress_draft_allowed ? "current" : "waiting"
            },
            { label: "Publikacja", state: "blocked" }
          ]}
        />
        <ContentSeoSignalPreview data={data} decision={selectedDecision} preflight={primaryPreflight} />
      </div>
    </div>
  );
}

function ContentNearestDecisionCard({
  decision,
  preflight
}: {
  decision: ContentDecisionItem | undefined;
  preflight: ContentPreflightItem | undefined;
}) {
  if (!decision) {
    return (
      <section className="rounded-md border border-action/30 bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold text-ink">Najbliższa decyzja</h2>
        <BlockerNotice message="Brak decyzji contentowych. Najpierw odśwież GSC, WordPress i dane pomocnicze." />
      </section>
    );
  }

  const url = decision.final_canonical_url ?? decision.intended_final_url ?? decision.page;
  const statusLabel = preflight?.status_label ?? decision.status_label ?? "do sprawdzenia";
  const modeLabel = preflight?.recommended_mode_label ?? decision.decision_type_label ?? "decyzja treści";
  const reviewRequired = !(preflight?.draft_allowed || preflight?.wordpress_draft_allowed);
  const metricEntries = contentPriorityMetricEntries(decision);
  const workflowHref = `/content-workflow?work_item_id=${encodeURIComponent(contentWorkItemId(decision))}`;

  return (
    <section className="overflow-hidden rounded-md border border-action/30 bg-white shadow-sm">
      <div className="flex min-h-12 items-center justify-between gap-3 border-b border-action/20 bg-blue-50 px-4 py-3">
        <h2 className="text-base font-semibold text-ink">Aktualna strona do pracy</h2>
        <StatusPill label={statusLabel} tone={reviewRequired ? "amber" : "green"} />
      </div>
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-blue-100 p-3 text-action">
            <BookOpenCheck aria-hidden="true" size={24} />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-normal text-action">
              {url ? shortPath(url) : "adres do ustalenia"}
            </p>
            <h3 className="mt-1 text-lg font-semibold leading-6 text-ink">
              {decision.wordpress_title_or_h1 ?? decision.title}
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {contentPlainDecisionReason(decision)}
            </p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <StatusPill label={modeLabel} tone="blue" />
          <StatusPill
            label={preflight?.sales_brief_allowed ? "plan treści możliwy" : "plan treści zablokowany"}
            tone={preflight?.sales_brief_allowed ? "green" : "red"}
          />
          <StatusPill label="publikacja zablokowana" tone="red" />
        </div>

        <div className="mt-4 grid gap-3 rounded-md border border-line bg-slate-50 p-3 md:grid-cols-5">
          {metricEntries.map(([label, value]) => (
            <MetricTile key={label} label={label} value={value} />
          ))}
        </div>

        <div className="mt-4 grid gap-2 text-sm leading-6 text-slate-700">
          <TraceLine
            label="WordPress"
            values={[
              decision.wordpress_title_or_h1 ? `Tytuł/H1: ${decision.wordpress_title_or_h1}` : undefined,
              decision.wordpress_match_label,
              decision.wordpress_match_confidence_label,
              decision.wordpress_modified_gmt ? `Modyfikacja: ${decision.wordpress_modified_gmt}` : undefined,
              decision.content_gate_summary
            ].filter(isPresentLabel)}
            empty="brak potwierdzonego wpisu albo strony WordPress"
          />
          <TraceLine
            label="Aktualne sekcje"
            values={decision.wordpress_section_headings.slice(0, 4)}
            empty="brak odczytu H2/sekcji dla tego URL"
          />
          <TraceLine
            label="Aktualna treść"
            values={[
              decision.wordpress_content_summary ?? undefined,
              decision.wordpress_content_word_count ? `${decision.wordpress_content_word_count} słów w odczycie REST` : undefined
            ].filter(isPresentLabel)}
            empty="brak bezpiecznego skrótu aktualnej treści"
          />
          {decision.wordpress_content_inventory_status === "missing" ? (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
              {decision.wordpress_content_inventory_note ??
                "WordPress nie wystawia bezpiecznego skrótu aktualnej treści dla tego URL."}
            </div>
          ) : null}
          <TraceLine
            label="Bloki WordPress"
            values={decision.wordpress_block_names.slice(0, 6)}
            empty="brak nazw bloków w odczycie REST"
          />
          <TraceLine
            label="Adres"
            values={url ? [shortPath(url)] : []}
            empty="adres do potwierdzenia przed szkicem"
          />
          {decision.wordpress_acf_section_inventory_status === "missing" ? (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
              {decision.wordpress_acf_section_inventory_note ??
                "Brakuje read-only kontraktu aktualnych wierszy ACF/flexible content. Nie rób rewrite z samego query."}
            </div>
          ) : null}
          <TraceLine
            label="Zapytania"
            values={decision.queries.slice(0, 5)}
            empty="brakuje potwierdzonych zapytań GSC"
          />
          <TraceLine
            label="Następny krok"
            values={[preflight?.next_step ?? decision.next_step]}
          />
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <a
            href={workflowHref}
            className="inline-flex h-10 items-center rounded-md bg-action px-4 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Otwórz workflow treści
          </a>
          {url ? (
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-10 items-center rounded-md border border-line bg-white px-4 text-sm font-semibold text-ink hover:bg-slate-50"
            >
              Otwórz publiczną stronę
            </a>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function ContentDevWorkspacePanel({
  authoringProfile
}: {
  authoringProfile: WordPressAuthoringProfile | undefined;
}) {
  const layouts = authoringProfile?.acf.layouts ?? [];
  const writeEnabled = Boolean(authoringProfile?.write_boundary.draft_writes_enabled_by_env);
  const acfLayouts = layouts.slice(0, 6).map((layout) => layout.label || layout.name);
  const acfLayoutCount = layouts.length;

  return (
    <section className="overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="flex min-h-12 items-center justify-between gap-3 border-b border-line bg-slate-50 px-4 py-3">
        <h2 className="text-base font-semibold text-ink">Dev i ACF</h2>
        <StatusPill label={writeEnabled ? "draft write włączony" : "draft write wyłączony"} tone={writeEnabled ? "green" : "amber"} />
      </div>
      <div className="grid gap-4 p-4 text-sm leading-6 text-slate-700">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Roboczy WordPress</p>
          <p className="mt-1 font-semibold text-ink">ekologus.dev.proudsite.pl</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Dev służy do pisania i układania nowych sekcji; nie traktuj dev hosta jako adresu kanonicznego.
            Publicznym punktem odniesienia SEO pozostaje ekologus.pl.
          </p>
        </div>
        <div className="grid gap-3 rounded-md border border-line bg-slate-50 p-3 sm:grid-cols-2">
          <MetricTile label="Tryb authoringu" value={authoringProfile?.authoring_target ?? "do sprawdzenia"} />
          <MetricTile label="Layouty ACF" value={acfLayoutCount} />
          <MetricTile label="REST WordPress" value={authoringProfile?.rest_api.status ?? "do sprawdzenia"} />
          <MetricTile label="WP-CLI" value={authoringProfile?.wp_cli.status ?? "do sprawdzenia"} />
        </div>
        <TraceLine
          label="Dostępne typy sekcji"
          values={acfLayouts}
          empty="brak odczytu layoutów ACF"
        />
        <TraceLine
          label="Co można zrobić"
          values={[
            "analizować obecną stronę publiczną",
            "przygotować plan nowych sekcji",
            writeEnabled ? "zapisać szkic na devie po akcji i review" : "przygotować draft package bez zapisu"
          ]}
        />
        <div className="flex flex-wrap gap-3">
          <a
            href="https://ekologus.dev.proudsite.pl/"
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-10 items-center rounded-md bg-action px-4 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Otwórz dev
          </a>
          <a
            href="https://ekologus.dev.proudsite.pl/wp-admin/"
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-10 items-center rounded-md border border-line bg-white px-4 text-sm font-semibold text-ink hover:bg-slate-50"
          >
            Otwórz WordPress admin
          </a>
        </div>
      </div>
    </section>
  );
}

function ContentCurrentSectionsPanel({ decision }: { decision: ContentDecisionItem | undefined }) {
  if (!decision) return null;
  const sections = decision.wordpress_section_headings.slice(0, 12);
  return (
    <section className="rounded-md border border-line bg-white p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-ink">Obecne sekcje publicznej strony</h2>
          <p className="mt-1 text-sm leading-5 text-slate-600">
            To jest aktualny układ, od którego marketer zaczyna pracę. Nowe sekcje na devie powinny uzupełniać ten układ, nie ignorować go.
          </p>
        </div>
        <StatusPill
          label={sections.length > 0 ? `${sections.length} sekcji` : "brak sekcji"}
          tone={sections.length > 0 ? "green" : "amber"}
        />
      </div>
      {sections.length > 0 ? (
        <ol className="grid gap-2 md:grid-cols-2">
          {sections.map((section, index) => (
            <li key={`${section}-${index}`} className="rounded-md border border-line bg-slate-50 px-3 py-2 text-sm leading-5 text-slate-700">
              <span className="mr-2 font-semibold text-action">{index + 1}.</span>
              {section}
            </li>
          ))}
        </ol>
      ) : (
        <BlockerNotice message="Brakuje odczytu sekcji. Najpierw pobierz aktualną strukturę strony albo pracuj w trybie nowych sekcji na devie bez claimów SEO." />
      )}
    </section>
  );
}

function ContentSeoSignalPreview({
  data,
  decision,
  preflight
}: {
  data: ContentDiagnosticsResponse;
  decision: ContentDecisionItem | undefined;
  preflight: ContentPreflightItem | undefined;
}) {
  const facts = uniqueMetricFacts([
    ...(decision?.metric_facts ?? []),
    ...data.sections.flatMap((section) => section.metric_facts)
  ]).slice(0, 4);
  const ahrefsRows = data.decision_queue.flatMap((item) => item.ahrefs_candidate_rows).slice(0, 2);

  return (
    <section className="rounded-md border border-line bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-ink">Podgląd sygnałów SEO</h2>
          <p className="mt-1 text-sm leading-5 text-slate-600">
            Sygnały pomagają wybrać review. Nie są obietnicą ruchu, leadów ani pozycji.
          </p>
        </div>
        <StatusPill label={data.evidence_summary_label} tone="purple" />
      </div>

      {facts.length > 0 ? (
        <div className="mt-4 grid grid-cols-2 gap-2 text-center text-xs">
          {facts.map((fact, index) => (
            <MetricTile
              key={`${fact.source_connector}-${fact.name}-${fact.evidence_id}-${index}`}
              label={fact.metric_label}
              value={formatContentMetricValue(fact.name, fact.value)}
            />
          ))}
        </div>
      ) : null}

      <div className="mt-4 grid gap-2 text-xs leading-5 text-slate-600">
        <TraceLine label="Źródła" values={data.source_connector_labels} />
        <TraceLine
          label="Preflight"
          values={[
            preflight?.inventory_gate_status_label,
            preflight?.canonical_gate_status_label,
            preflight?.duplicate_gate_status_label,
            preflight?.claim_gate_status_label
          ].filter(isPresentLabel)}
          empty="bramka preflight nie jest jeszcze dostępna"
        />
        <TraceLine
          label="Ahrefs pomocniczo"
          values={ahrefsRows.map((row) => `${row.topic}: ${row.relevance_status_label || "do sprawdzenia"}`)}
          empty="brak pomocniczych rekordów Ahrefs"
        />
      </div>
    </section>
  );
}

function contentPriorityMetricEntries(decision: ContentDecisionItem) {
  const preferredLabels = ["zapytania", "wyświetlenia", "kliknięcia", "CTR", "pozycja", "sekcje WP"];
  const entries: Array<[string, string | number]> = [];
  for (const label of preferredLabels) {
    const value = decision.metric_tiles[label];
    if (typeof value === "string" || typeof value === "number") {
      entries.push([label, value]);
    }
  }

  if (entries.length >= 4) return entries.slice(0, 5);

  const fallbackEntries = Object.entries(decision.metric_tiles).filter(
    (entry): entry is [string, string | number] =>
      !preferredLabels.includes(entry[0]) &&
      (typeof entry[1] === "string" || typeof entry[1] === "number")
  );
  return [...entries, ...fallbackEntries].slice(0, 5);
}

function contentPlainDecisionReason(decision: ContentDecisionItem) {
  const url = decision.final_canonical_url ?? decision.intended_final_url ?? decision.page;
  if (decision.wordpress_match === "found" && url) {
    const sectionLabel =
      decision.wordpress_section_count && decision.wordpress_section_count > 0
        ? `${decision.wordpress_section_count} sekcji`
        : "potwierdzone sekcje";
    const queryLabel =
      decision.query_count && decision.query_count > 0
        ? `${decision.query_count} zapytań z GSC`
        : "zapytania z GSC";
    return `Pracuj na istniejącej stronie ${shortPath(url)}. WordPress potwierdza aktualny URL, ${sectionLabel} i ${queryLabel}. Najpierw porównaj obecne sekcje z query, potem zdecyduj: odświeżyć, scalić albo zostawić.`;
  }
  if (decision.source_connectors.includes("ahrefs")) {
    return "To jest tylko trop z Ahrefs. Bez publicznego URL-a, spisu treści i zamkniętej duplikacji nie zaczynaj pisania.";
  }
  return decision.summary ?? decision.rationale;
}

function contentWorkItemId(decision: ContentDecisionItem) {
  return `content_work_item_${decision.id}`;
}

function contentPlannerStatTiles(
  data: ContentDiagnosticsResponse,
  preflight: ContentPreflightItem | undefined
) {
  const metricTiles = contentOperatorMetricTiles(data);
  const ahrefsDecisionCount = data.decision_queue.filter((decision) =>
    decision.source_connectors.includes("ahrefs")
  ).length;

  return [
    {
      value: metricTiles[0]?.[1] ?? data.query_page_count,
      label: metricTiles[0]?.[0] ?? "Zapytania i adresy z GSC",
      actionLabel: "Sprawdź popyt",
      tone: "blue" as const,
      icon: <SearchCheck aria-hidden="true" size={22} />
    },
    {
      value: metricTiles[1]?.[1] ?? data.matched_inventory_count,
      label: metricTiles[1]?.[0] ?? "Treści znalezione w WordPress",
      actionLabel: "Chroń przed duplikatem",
      tone: "green" as const,
      icon: <FileText aria-hidden="true" size={22} />
    },
    {
      value: metricTiles[2]?.[1] ?? ahrefsDecisionCount,
      label: metricTiles[2]?.[0] ?? "Ahrefs pomocniczo",
      actionLabel: "Tylko trop do review",
      tone: "purple" as const,
      icon: <TrendingUp aria-hidden="true" size={22} />
    },
    {
      value: preflight?.recommended_mode_label ?? data.decision_queue.length,
      label: preflight ? "Najbliższa bramka treści" : "Decyzje treści",
      actionLabel: preflight?.wordpress_draft_allowed ? "Szkic po review" : "Publikacja zablokowana",
      tone: preflight?.wordpress_draft_allowed ? ("green" as const) : ("red" as const),
      icon: <ShieldAlert aria-hidden="true" size={22} />
    }
  ];
}

function contentSourceFreshnessItems(data: ContentDiagnosticsResponse) {
  const refreshByConnector = new Map(
    data.latest_refreshes.map((refresh) => [refresh.connector_id, refresh])
  );
  const sources = [
    { id: "google_search_console", label: "GSC", icon: <SearchCheck aria-hidden="true" size={16} /> },
    { id: "wordpress_ekologus", label: "WordPress", icon: <FileText aria-hidden="true" size={16} /> },
    { id: "ahrefs", label: "Ahrefs", icon: <TrendingUp aria-hidden="true" size={16} /> }
  ];

  const items = sources.map((source) => {
    const connector = data.connectors.find((item) => item.id === source.id);
    const refresh = refreshByConnector.get(source.id);
    const connectorLabel = refresh ? refresh.connector_label : connector?.label ?? source.label;
    const status = refresh ? refresh.status_label : connector ? connector.status_label : "do sprawdzenia";
    return {
      label: source.label,
      detail: connectorLabel === source.label ? status : `${connectorLabel}: ${status}`,
      tone: contentFreshnessTone(refresh?.status ?? connector?.status),
      icon: source.icon
    };
  });

  return [
    ...items,
    {
      label: "Treści",
      detail: data.freshness_assessment.state_label,
      tone: data.freshness_assessment.requires_refresh ? ("amber" as const) : ("green" as const),
      icon: <ListChecks aria-hidden="true" size={16} />
    }
  ];
}

function contentFreshnessTone(status: string | undefined) {
  if (status === "completed" || status === "configured" || status === "ready") return "green" as const;
  if (status === "missing_credentials" || status === "blocked" || status === "failed") return "red" as const;
  if (status === "stale" || status === "pending") return "amber" as const;
  return "neutral" as const;
}

function contentBlockerPanelItems(
  data: ContentDiagnosticsResponse,
  preflight: ContentPreflightItem | undefined
) {
  const firstBlockedClaims = contentForbiddenClaims(data, preflight).slice(0, 4);
  const baseItems = firstBlockedClaims.map((claim) => ({
    title: claim,
    description: "Blokada pozostaje aktywna bez dowodu, preflightu i review człowieka.",
    tone: "red" as const
  }));

  return [
    ...baseItems,
    {
      title: "Publikacja bez review",
      description: preflight?.wordpress_draft_allowed
        ? "Nawet przygotowany szkic wymaga potwierdzenia przed zapisem i publikacją."
        : "WordPress pozostaje zablokowany; można pracować tylko na planie i podglądzie.",
      tone: "red" as const
    },
    {
      title: "Ahrefs jako uzasadnienie publikacji",
      description: "Ahrefs jest pomocniczym tropem. Decyzję treści muszą potwierdzić GSC, WordPress i bramka treści.",
      tone: "amber" as const
    }
  ].slice(0, 5);
}

function contentForbiddenClaims(
  data: ContentDiagnosticsResponse,
  preflight: ContentPreflightItem | undefined
) {
  return uniqueValues([
    ...data.operator_summary.blocked_claim_labels,
    ...data.sections.flatMap((section) => section.blocked_claim_labels),
    ...data.decision_queue.flatMap((decision) => decision.blocked_claim_labels),
    ...(preflight?.blocked_claims ?? []),
    "publikacja bez review",
    "Ahrefs jako samodzielne uzasadnienie publikacji"
  ]).slice(0, 8);
}

function contentQueueRows(data: ContentDiagnosticsResponse) {
  return data.decision_queue.map((decision) => {
    const gateLabel =
      decision.duplicate_gate_status_label ??
      decision.inventory_gate_status_label ??
      decision.canonical_gate_status_label ??
      "review wymagany";

    const url = decision.final_canonical_url ?? decision.intended_final_url ?? decision.page;
    return {
      id: decision.id,
      title: decision.title,
      detail: [
        url ? shortPath(url) : decision.primary_query ?? decision.decision_type_label,
        decision.wordpress_title_or_h1 ? `Tytuł/H1: ${decision.wordpress_title_or_h1}` : undefined,
        wordpressSectionSummary(decision),
        decision.wordpress_match_label,
        decision.wordpress_match_confidence_label
      ].filter(isPresentLabel).join(" · "),
      modeLabel: decision.decision_type_label || "decyzja treści",
      modeTone: decision.source_connectors.includes("ahrefs") ? ("purple" as const) : ("blue" as const),
      signals: contentQueueSignals(decision),
      gateLabel,
      risk: contentDecisionRisk(decision),
      nextStep: decision.next_step
    };
  });
}

function contentQueueSignals(decision: ContentDecisionItem) {
  const metricTiles = Object.entries(decision.metric_tiles).slice(0, 3).map(([label, value]) => `${label}: ${value}`);
  const wordpressSignal = decision.wordpress_title_or_h1 ? [`WP: ${decision.wordpress_title_or_h1}`] : [];
  const sectionSignal = wordpressSectionSummary(decision) ? [wordpressSectionSummary(decision)] : [];
  const querySignal = decision.primary_query ? [`zapytanie: ${decision.primary_query}`] : [];
  const sourceSignal = decision.source_connector_labels.length
    ? [`źródła: ${decision.source_connector_labels.join(", ")}`]
    : [];
  return [...wordpressSignal, ...sectionSignal, ...metricTiles, ...querySignal, ...sourceSignal].slice(0, 4);
}

function wordpressSectionSummary(decision: ContentDecisionItem) {
  if (decision.wordpress_section_inventory_status === "available") {
    const count = decision.wordpress_section_count ?? decision.wordpress_section_headings.length;
    return count > 0 ? `sekcje WP: ${count}` : "sekcje WP: dostępne";
  }
  if (decision.wordpress_match === "found") {
    return "sekcje WP: brak odczytu";
  }
  return undefined;
}

function contentDecisionRisk(decision: ContentDecisionItem) {
  if (decision.risk === "high") return "high" as const;
  if (decision.risk === "medium") return "medium" as const;
  if (decision.status === "blocked") return "blocked" as const;
  if (decision.risk === "low") return "low" as const;
  return "unknown" as const;
}

function uniqueMetricFacts(facts: ContentMetricFact[]) {
  const seen = new Set<string>();
  return facts.filter((fact) => {
    const key = `${fact.source_connector}:${fact.name}:${fact.evidence_id}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function ContentExpandableBriefPanel({ actions }: { actions: ActionObject[] }) {
  const [showBriefs, setShowBriefs] = useState(false);
  const briefCount = contentActionPreviewCardsFromActions(actions, "content_brief_review").length;
  const draftCount = contentActionPreviewCardsFromActions(
    actions,
    "wordpress_draft_payload_review"
  ).length;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Plany treści do sprawdzenia
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Pierwszy ekran pokazuje jeden wybrany kierunek treści. Rozwiń plany treści,
            gdy chcesz zobaczyć H1, H2, FAQ, CTA, blokady publikacji i szkice
            WordPress do sprawdzenia.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs">
          <MetricTile label="Plany treści" value={briefCount} />
          <MetricTile label="Szkice" value={draftCount} />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowBriefs((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showBriefs ? "Ukryj plany treści" : "Pokaż plany treści"}
      </button>

      {showBriefs ? <div className="mt-4"><ContentBriefPreviewPanel actions={actions} /></div> : null}
    </section>
  );
}

function ContentExpandableReviewPanel({ data }: { data: ContentDiagnosticsResponse }) {
  const [showReview, setShowReview] = useState(false);
  const operatorMetricTiles = contentOperatorMetricTiles(data);

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Pełny przegląd treści
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Rozwiń pełny przegląd, gdy chcesz zobaczyć kolejkę decyzji, status
            WordPress, GSC i Ahrefs, dowody w WILQ i bramę bezpieczeństwa treści.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          {operatorMetricTiles.slice(1, 4).map(([label, value]) => (
            <MetricTile key={label} label={label} value={value} />
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowReview((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showReview ? "Ukryj pełny przegląd treści" : "Pokaż pełny przegląd treści"}
      </button>

      {showReview ? (
        <div className="mt-4 grid gap-6">
          <ContentOperatorSummary data={data} />
          <ContentDiagnosticProof data={data} />
          <ContentSafetyGatePanel data={data} />
        </div>
      ) : null}
    </section>
  );
}

function ContentExpandableActionsPanel({
  actions,
  actionIds,
  actionSummaryLabel,
  isLoading,
  isError
}: {
  actions: ActionObject[];
  actionIds: string[];
  actionSummaryLabel: string;
  isLoading: boolean;
  isError: boolean;
}) {
  const [showActions, setShowActions] = useState(false);

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Akcje do sprawdzenia
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ pokazuje dla Treści: {actionSummaryLabel}.
            Otwórz tę sekcję dopiero wtedy, gdy chcesz zapisać decyzję człowieka,
            wygenerować podgląd zmian albo sprawdzić warunki bezpiecznego zapisu.
          </p>
        </div>
        <MetricTile label="Akcje" value={actionSummaryLabel} />
      </div>

      <button
        type="button"
        onClick={() => setShowActions((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showActions ? "Ukryj akcje do sprawdzenia" : "Pokaż akcje do sprawdzenia"}
      </button>

      {showActions ? (
        <div className="mt-4">
          {isLoading ? (
            <ActionIdFocus
              actionIds={actionIds}
              actionSummaryLabel={actionSummaryLabel}
              note="Ładuję szczegóły akcji; decyzje contentowe powyżej są już oparte o dane WILQ."
            />
          ) : isError ? (
            <ActionIdFocus
              actionIds={actionIds}
              actionSummaryLabel={actionSummaryLabel}
              note="Nie udało się odczytać pełnych akcji. Linki do sprawdzenia zostają widoczne, ale podgląd zmian wymaga danych akcji."
            />
          ) : (
            <ActionFocus actions={actions} />
          )}
        </div>
      ) : null}
    </section>
  );
}

function ContentPreflightPanel({
  data,
  isLoading,
  isError
}: {
  data: ContentPreflightResponse | undefined;
  isLoading: boolean;
  isError: boolean;
}) {
  const item = data?.primary_item;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Plan pracy nad treścią
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Najpierw wybierz tryb pracy dla konkretnego URL-a: zachować,
            odświeżyć, scalić, utworzyć albo zablokować. Szkic na devie jest
            kolejnym krokiem dopiero po planie i sprawdzeniu obietnic.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          <MetricTile label="Tryb" value={item ? item.recommended_mode_label : "nie pisz"} />
          <MetricTile label="Status" value={item ? item.status_label : "bramka niedostępna"} />
          <MetricTile label="Blokady" value={data?.blocker_count ?? 0} />
          <MetricTile label="Plan treści" value={item?.sales_brief_allowed ? "możliwy" : "zablokowany"} />
        </div>
      </div>

      {isLoading ? (
        <p className="mt-3 text-sm text-slate-600">WILQ sprawdza bramkę pisania.</p>
      ) : isError || !data || !item ? (
        <BlockerNotice message="Nie udało się odczytać bramki pisania. Nie zaczynaj szkicu bez wyniku sprawdzenia." />
      ) : (
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          <div className="rounded-md border border-line bg-slate-50 p-3">
            <h3 className="text-sm font-semibold text-ink">Rekomendowany kierunek</h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {contentPreflightModeSentence(item)}
            </p>
            <TraceLine
              label="Adres"
              values={[
                item.final_canonical_url ?? item.intended_final_url ?? item.source_public_url ?? ""
              ].filter(Boolean).map(shortPath)}
              empty="do potwierdzenia"
            />
          </div>
          <div className="rounded-md border border-line bg-slate-50 p-3">
            <h3 className="text-sm font-semibold text-ink">Następny krok</h3>
            <p className="mt-2 text-sm font-medium leading-6 text-ink">{item.next_step}</p>
            <TraceLine label="Wspólne zapytania" values={[item.query_overlap_summary]} />
          </div>
          <div className="rounded-md border border-line bg-white p-3">
            <h3 className="text-sm font-semibold text-ink">Co blokuje szkic</h3>
            <TraceLine
              label="Brakuje"
              values={item.missing_inputs.slice(0, 5)}
              empty="WILQ nie zgłosił dodatkowych brakujących wejść w tej bramce."
            />
            <TraceLine
              label="Zakazy"
              values={item.blocked_claims.slice(0, 5)}
              empty="WILQ nie zgłosił dodatkowych zakazanych obietnic w tej bramce."
            />
          </div>
          <div className="rounded-md border border-line bg-white p-3">
            <h3 className="text-sm font-semibold text-ink">Dowody i istniejące treści</h3>
            <TraceLine
              label="Podobne URL-e"
              values={item.similar_existing_urls.slice(0, 4).map(shortPath)}
              empty="WILQ nie potwierdził podobnych URL-i; przed tworzeniem nadal sprawdź spis treści."
            />
            <TraceLine
              label="Dowody"
              values={[item.evidence_summary_label]}
            />
          </div>
        </div>
      )}
    </section>
  );
}

function ContentSafetyGatePanel({ data }: { data: ContentDiagnosticsResponse }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa treści
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              WILQ może przygotować plan treści, kolejkę odświeżenia i podgląd zmian,
              ale nie publikuje ani nie zmienia WordPress bez sprawdzenia w WILQ,
              jawnej zgody operatora i audytu.
            </p>
          </div>
        </div>
        <TraceLine
          label="Nie wolno twierdzić"
          values={data.sections.flatMap((section) => section.blocked_claim_labels)}
        />
      </section>
  );
}

function ContentBriefPreviewPanel({ actions }: { actions: ActionObject[] }) {
  const previews = contentActionPreviewCardsFromActions(actions, "content_brief_review").slice(0, 4);
  const draftPreviews = contentActionPreviewCardsFromActions(
    actions,
    "wordpress_draft_payload_review"
  ).slice(0, 4);
  if (previews.length === 0 && draftPreviews.length === 0) return null;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Plany treści do sprawdzenia
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            Co WILQ może przygotować bez publikacji
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            To są propozycje do sprawdzenia w WILQ. Każda wymaga kontroli
            GSC i WordPress, duplikatów i decyzji operatora przed jakąkolwiek
            zmianą treści.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs">
          <MetricTile label="Podglądy" value={previews.length} />
          <MetricTile
            label="Zapis zmian"
            value="zablokowane"
          />
        </div>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {previews.map(({ actionId, card }) => (
          <div key={`${actionId}-${card.id}`} className="grid gap-2">
            <ActionPreviewCard card={card} />
            <a className="text-xs font-medium text-ink underline" href={`/actions/${actionId}`}>
              Otwórz akcję do sprawdzenia
            </a>
          </div>
        ))}
      </div>
      {draftPreviews.length > 0 ? (
        <div className="mt-5 rounded-md border border-line bg-white p-3">
          <div className="mb-3">
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
              Szkic WordPress po sprawdzeniu
            </div>
            <h3 className="mt-1 text-sm font-semibold text-ink">
              Co WILQ może przygotować jako szkic WordPress
            </h3>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              Te szkice pojawiają się dopiero po zapisanym sprawdzeniu propozycji.
              Status pozostaje jako szkic, a zmiany i publikacja są zablokowane.
            </p>
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            {draftPreviews.map(({ actionId, card }) => (
              <div key={`${actionId}-${card.id}`} className="grid gap-2">
                <ActionPreviewCard card={card} />
                <a className="text-xs font-medium text-ink underline" href={`/actions/${actionId}`}>
                  Otwórz akcję do sprawdzenia
                </a>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function contentSelectedPrimaryDecision(data: ContentDiagnosticsResponse) {
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const confirmedPublicContent = data.decision_queue.find((decision) =>
    Boolean(decision.page || decision.final_canonical_url || decision.intended_final_url) &&
    decision.wordpress_match === "found" &&
    decision.wordpress_section_headings.length > 0
  );
  if (confirmedPublicContent) return confirmedPublicContent;

  const selectedDecisionId = data.marketer_decision?.technical_decision_id;
  if (selectedDecisionId) return decisionsById.get(selectedDecisionId) ?? data.decision_queue[0];
  const topDecisionId = data.operator_summary.top_decision_ids[0];
  if (topDecisionId) return decisionsById.get(topDecisionId) ?? data.decision_queue[0];
  return data.decision_queue[0];
}

function ContentOperatorSummary({ data }: { data: ContentDiagnosticsResponse }) {
  const summary = data.operator_summary;
  const operatorMetricTiles = contentOperatorMetricTiles(data);
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const topDecisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is ContentDecisionItem => Boolean(decision));
  const actionIds = summary.action_ids;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Przegląd treści
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            {summary.title}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {summary.summary}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          {operatorMetricTiles.map(([label, value]) => (
            <MetricTile key={label} label={label} value={value} />
          ))}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {topDecisions.length > 0 ? (
            topDecisions.map((decision) => (
              <ContentDecisionCard key={decision.id} decision={decision} />
            ))
          ) : (
            <BlockerNotice message="Brak decyzji contentowych. Najpierw uruchom odczyt GSC i WordPress." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb treści</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine
              label="Tryby decyzji"
              values={summary.decision_type_labels}
              empty="WILQ nie podał trybów decyzji; nie wybieraj pisania bez sprawdzenia."
            />
            <TraceLine
              label="Dopasowania WordPress"
              values={[
                `potwierdzone: ${summary.confirmed_wordpress_count}`,
                `brak potwierdzenia: ${summary.missing_wordpress_count}`
              ]}
            />
            <TraceLine
              label="Publiczne URL-e"
              values={[
                `potwierdzone URL-e: ${summary.current_site_match_count}`
              ]}
            />
            <TraceLine
              label="Dowody"
              values={[summary.evidence_summary_label]}
              empty="WILQ nie podał dowodów źródłowych; nie traktuj przeglądu jako rekomendacji."
            />
            <TraceLine label="Akcje" values={[summary.action_summary_label]} />
            <TraceLine
              label="Nie wolno twierdzić"
              values={summary.blocked_claim_labels}
            />
          </div>
          {actionIds.length > 0 ? (
            <a
              href={`/actions/${actionIds[0]}`}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
            >
              Sprawdź w WILQ
            </a>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function contentOperatorMetricTiles(data: ContentDiagnosticsResponse) {
  return Object.entries(data.operator_summary.metric_tiles);
}

function ContentDecisionCard({
  decision
}: {
  decision: ContentDecisionItem;
}) {
  const canonicalUrl = decision.final_canonical_url ?? decision.intended_final_url;
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{contentDecisionTitle(decision)}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {decision.decision_type_label || "typ decyzji do sprawdzenia"}
          </p>
        </div>
        <StatusBadge value={decision.status} label={decision.status_label} />
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">
        {decision.summary ?? decision.rationale}
      </p>
      {decision.summary ? (
        <p className="mt-1 text-xs leading-5 text-slate-500">{decision.rationale}</p>
      ) : null}
      <p className="mt-2 text-sm font-medium text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
        {decision.page ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Strona: {shortPath(decision.page)}
          </span>
        ) : null}
        {decision.queries.length > 0 ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Zapytania: {decision.queries.slice(0, 4).join(", ")}
          </span>
        ) : null}
        {decision.wordpress_match ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            WordPress: {decision.wordpress_match_label || "stan spisu do sprawdzenia"}
          </span>
        ) : null}
        {decision.wordpress_match_confidence ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Dopasowanie: {decision.wordpress_match_confidence_label || "pewność dopasowania do sprawdzenia"}
          </span>
        ) : null}
        {canonicalUrl ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Kanoniczny: {shortPath(canonicalUrl)}
          </span>
        ) : null}
        {decision.preview_url ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Podgląd: {shortPath(decision.preview_url)}
          </span>
        ) : null}
        {decision.inventory_gate_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Spis: {decision.inventory_gate_status_label || "status spisu do sprawdzenia"}
          </span>
        ) : null}
        {decision.canonical_gate_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Kanoniczny: {decision.canonical_gate_status_label || "status URL kanonicznego do sprawdzenia"}
          </span>
        ) : null}
        {decision.duplicate_gate_status ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Duplikaty: {decision.duplicate_gate_status_label || "status duplikatów do sprawdzenia"}
          </span>
        ) : null}
      </div>
      {decision.content_gate_summary ? (
        <p className="mt-2 rounded border border-line bg-white px-3 py-2 text-xs text-slate-700">
          {decision.content_gate_summary}
        </p>
      ) : null}
      {decision.ahrefs_candidate_rows.length > 0 ? (
        <div className="mt-3 rounded-md border border-line bg-white p-3">
          <h4 className="text-sm font-semibold text-ink">Ahrefs: akcje do sprawdzenia</h4>
          <div className="mt-2 grid gap-2">
            {decision.ahrefs_candidate_rows.slice(0, 3).map((candidate) => (
              <div key={candidate.id} className="rounded border border-line bg-slate-50 p-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-ink">{candidate.topic}</div>
                    <LabelChipRow
                      className="mt-1 gap-1"
                      chips={[
                        { label: "Typ", value: candidate.gap_type_label || "typ luki do sprawdzenia" },
                        { label: "Trafność", value: candidate.relevance_status_label || "trafność do sprawdzenia" },
                        { label: "Ocena WILQ", value: candidate.relevance_score }
                      ]}
                    />
                  </div>
                  <div className="flex flex-wrap gap-1 text-xs">
                    <span className="rounded border border-line bg-white px-2 py-1">
                      GSC: {candidate.gsc_demand_label || "popyt GSC do sprawdzenia"}
                    </span>
                    <span className="rounded border border-line bg-white px-2 py-1">
                      WP: {candidate.wordpress_inventory_match_label || "spis WordPress do sprawdzenia"}
                    </span>
                  </div>
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-600">{candidate.next_step}</p>
                <TraceLine
                  label="Powody"
                  values={candidate.business_relevance_reason_labels}
                />
                <TraceLine
                  label="Wspólne zapytania GSC"
                  values={candidate.gsc_overlap_terms.slice(0, 3)}
                  empty="WILQ nie potwierdził wspólnych zapytań w GSC; traktuj propozycję jako sprawdzenie."
                />
                <TraceLine
                  label="Powiązane URL-e WordPress"
                  values={candidate.wordpress_overlap_urls.map(shortPath).slice(0, 3)}
                  empty="WILQ nie potwierdził powiązanych URL-i WordPress; sprawdź spis przed tworzeniem."
                />
              </div>
            ))}
          </div>
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Dowody"
          values={[decision.evidence_summary_label]}
          empty="WILQ nie podał dowodów źródłowych; nie traktuj tej decyzji jako rekomendacji."
        />
        <TraceLine label="Źródła" values={decision.source_connector_labels} />
        <TraceLine label="Akcje" values={[decision.action_summary_label]} />
        <TraceLine label="Nie wolno twierdzić" values={decision.blocked_claim_labels} />
      </div>
      {decision.metric_facts.length > 0 ? (
        <ContentMetricTiles facts={decision.metric_facts.slice(0, 4)} />
      ) : null}
    </article>
  );
}

function ContentDiagnosticProof({ data }: { data: ContentDiagnosticsResponse }) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  const visibleMetricFacts = metricFacts.slice(0, 4);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i warunki decyzji treści
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót danych i ograniczeń WILQ. Decyzje dla marketera są powyżej;
            tutaj widać, z jakich źródeł i blokad wynikają.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Sekcje danych" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Dowody" value={data.evidence_summary_label} />
        </div>
      </div>
      {visibleMetricFacts.length > 0 ? <ContentMetricTiles facts={visibleMetricFacts} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={data.sections.map((section) => section.title)} />
        <TraceLine label="Źródła danych" values={data.source_connector_labels} />
        <TraceLine label="Akcje" values={[data.action_summary_label]} />
        <TraceLine
          label="Nie wolno twierdzić"
          values={data.sections.flatMap((section) => section.blocked_claim_labels)}
        />
      </div>
    </section>
  );
}

function ContentMetricTiles({ facts }: { facts: ContentMetricFact[] }) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
      {facts.map((fact, index) => (
        <MetricTile
          key={`${fact.source_connector}-${fact.name}-${fact.evidence_id}-${index}`}
          label={fact.metric_label}
          value={formatContentMetricValue(fact.name, fact.value)}
        />
      ))}
    </div>
  );
}

function contentPreflightModeSentence(item: ContentPreflightItem) {
  if (item.recommended_mode === "preserve") {
    return "Najbezpieczniej zachować istniejącą treść. Nie ma jeszcze powodu, żeby ją przepisywać.";
  }
  if (item.recommended_mode === "refresh") {
    return "WILQ wskazuje odświeżenie istniejącej treści. Nowy artykuł pozostaje zablokowany.";
  }
  if (item.recommended_mode === "merge") {
    return "WILQ wskazuje scalenie albo decyzję o połączeniu tematów przed pisaniem.";
  }
  if (item.recommended_mode === "create") {
    return "WILQ dopuszcza nową treść, ale szkic nadal wymaga planu treści, sprawdzenia ryzykownych obietnic i decyzji człowieka.";
  }
  return "WILQ blokuje pisanie. Najpierw trzeba uzupełnić brakujące dane albo rozwiązać ryzyko.";
}

function contentDecisionTitle(decision: ContentDecisionItem) {
  return decision.title;
}

function contentActionPreviewCardsFromActions(actions: ActionObject[], kind: string) {
  return actions.flatMap((action) =>
    action.preview_cards
      .filter((card) => card.kind === kind)
      .map((card) => ({ actionId: action.id, card }))
  );
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}

function isPresentLabel(value: string | null | undefined): value is string {
  return Boolean(value);
}
