import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ClipboardCheck, ShieldAlert } from "lucide-react";

import { getLocaloDiagnostics, LocaloDiagnosticsResponse } from "../lib/api";
import { MetricFactChips } from "../components/MetricFactChips";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import { priorityLabel } from "./marketingLabels";

type LocaloDecisionItem = LocaloDiagnosticsResponse["decision_queue"][number];

export function LocaloDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["localo-diagnostics"],
    queryFn: getLocaloDiagnostics
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/localo/diagnostics. Localo route nie może udawać rankingów, GBP ani lokalnej widoczności bez WILQ API." />
      </main>
    );
  }

  const data = diagnostics.data;
  const latestRefresh = data.latest_refresh;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Localo</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Localo z WILQ API. Oddziela dostęp MCP od lokalnych
            rankingów, GBP, konkurencji i reviews, żeby marketer nie dostał
            fałszywej rekomendacji lokalnego SEO.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Fakty lokalne" value={data.visibility_fact_count} />
          <MetricTile label="Braki danych" value={data.operator_summary.missing_read_contracts.length} />
          <MetricTile label="Blokady" value={data.blocker_count} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Localo / widoczność lokalna
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.connector.id}: {localoConnectorStatusLabel(data.connector.status)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {localoAccessStatusLabel(data.access_probe.status)}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {localoRefreshStatusLabel(latestRefresh.status)}
              </span>
            ) : null}
          </div>
        </div>
        <p className="mt-3 text-sm leading-6 text-slate-700">{data.access_probe.summary}</p>
        {latestRefresh?.errors.length ? (
          <div className="mt-3 rounded-md border border-risk/30 bg-risk/10 p-3 text-sm text-risk">
            {latestRefresh.errors[0]}
          </div>
        ) : null}
      </section>

      <LocaloVisibilitySnapshot data={data} />
      <LocaloOperatorSummary data={data} />
      <LocaloDiagnosticProof data={data} />

      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa Localo/GBP
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              MCP initialize potwierdza tylko dostęp adaptera. WILQ nie publikuje
              postów GBP, nie zmienia profilu i nie obiecuje poprawy widoczności
              bez ranking/GBP evidence, ActionObject, walidacji i audytu.
            </p>
          </div>
        </div>
        <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <LinkedTraceLine label="Dowody" values={data.evidence_ids} kind="evidence" />
          <TraceLine label="Źródła" values={["localo"]} />
          <TraceLine
            label="Zablokowane claimy"
            values={uniqueValues(
              data.decision_queue.flatMap((decision) =>
                decision.blocked_claims.map(localoBlockedClaimLabel)
              )
            )}
          />
          <TraceLine
            label="Brakujące kontrakty"
            values={uniqueValues(
              data.decision_queue.flatMap((decision) =>
                decision.missing_read_contracts.map(localoMissingContractLabel)
              )
            )}
          />
        </div>
      </section>
    </main>
  );
}

function LocaloVisibilitySnapshot({ data }: { data: LocaloDiagnosticsResponse }) {
  const visibilityDecision =
    data.decision_queue.find((decision) => decision.decision_type === "review_local_visibility") ??
    data.decision_queue.find((decision) => decision.status === "ready") ??
    data.decision_queue[0];
  const metricEntries = Object.entries(visibilityDecision?.metric_tiles ?? {}).filter(
    ([label]) => label !== "dostęp MCP"
  );

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
          Snapshot lokalnej widoczności
        </h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          To jest marketerowy skrót z Localo facts dostępnych w WILQ API. MCP/OAuth
          zostają jako techniczny proof niżej, a lokalne claimy pozostają
          zablokowane, jeśli brakuje ranking/GBP/review evidence.
        </p>
      </div>
      {visibilityDecision ? (
        <div className="rounded-md border border-line p-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold">Localo facts w WILQ API</h3>
              <p className="mt-2 text-sm leading-6 text-slate-700">
                {visibilityDecision.summary}
              </p>
            </div>
            <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-ink">
              {localoDecisionStatusLabel(visibilityDecision.status)}
            </span>
          </div>
          {metricEntries.length > 0 ? (
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
              {metricEntries.map(([label, value]) => (
                <MetricTile
                  key={`${visibilityDecision.id}-snapshot-${label}`}
                  label={label}
                  value={value}
                />
              ))}
            </div>
          ) : (
            <BlockerNotice message="Brak Localo facts do snapshotu. WILQ pokazuje tylko stan dostępu i blokuje lokalne rekomendacje." />
          )}
          <p className="mt-3 text-sm font-semibold leading-6 text-ink">
            {visibilityDecision.next_step}
          </p>
        </div>
      ) : (
        <BlockerNotice message="Brak decyzji Localo z WILQ API. Snapshot lokalny nie może zostać zbudowany." />
      )}
    </section>
  );
}

function LocaloOperatorSummary({ data }: { data: LocaloDiagnosticsResponse }) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const decisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is LocaloDecisionItem => Boolean(decision));
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            {summary.title}
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {summary.summary}
          </p>
        </div>
      </div>
      {decisions.length === 0 ? (
        <BlockerNotice message="Brak decyzji Localo z WILQ API. Widok nie wygeneruje lokalnej rekomendacji z pustego stanu." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {decisions.map((decision) => (
            <LocaloDecisionCard key={decision.id} decision={decision} />
          ))}
        </div>
      )}
    </section>
  );
}

function LocaloDecisionCard({ decision }: { decision: LocaloDecisionItem }) {
  const marketerMetricTiles = Object.entries(decision.metric_tiles ?? {}).filter(
    ([label]) => label !== "dostęp MCP"
  );

  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Localo / {localoDecisionTypeLabel(decision.decision_type)} /{" "}
            {priorityLabel(decision.priority)}
          </p>
          <h3 className="mt-1 text-base font-semibold">{decision.title}</h3>
        </div>
        <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-ink">
          {localoDecisionStatusLabel(decision.status)}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{decision.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{decision.rationale}</p>
      <p className="mt-3 text-sm font-semibold leading-6 text-ink">{decision.next_step}</p>
      {marketerMetricTiles.length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {marketerMetricTiles.map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine label="Access" values={[localoAccessStatusLabel(decision.access_status)]} />
        <TraceLine
          label="Dozwolone evidence"
          values={decision.allowed_evidence.map(localoAllowedEvidenceLabel)}
        />
        <TraceLine
          label="Brakujące kontrakty"
          values={decision.missing_read_contracts.map(localoMissingContractLabel)}
        />
        <TraceLine
          label="Blokady claimów"
          values={decision.blocked_claims.map(localoBlockedClaimLabel)}
        />
        <LinkedTraceLine label="Dowody" values={decision.evidence_ids} kind="evidence" />
      </div>
      {decision.metric_facts.length > 0 ? (
        <MetricFactChips facts={decision.metric_facts.slice(0, 6)} />
      ) : null}
    </article>
  );
}

function LocaloDiagnosticProof({ data }: { data: LocaloDiagnosticsResponse }) {
  const [showTechnicalProof, setShowTechnicalProof] = useState(false);
  const probe = data.access_probe;
  return (
    <section className="mt-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i ograniczenia Localo
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            WILQ pokazuje access proof osobno od lokalnych facts. Brak facts oznacza
            brak diagnozy rankingów, nie zaproszenie do zgadywania.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowTechnicalProof((current) => !current)}
          className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
        >
          {showTechnicalProof ? "Ukryj techniczny proof Localo" : "Pokaż techniczny proof Localo"}
        </button>
      </div>
      {showTechnicalProof ? (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <MetricTile label="MCP initialize" value={probe.mcp_initialize_status ?? "brak"} />
            <MetricTile
              label="OAuth code"
              value={localoBooleanLabel(probe.authorization_code_supported)}
            />
            <MetricTile label="PKCE S256" value={localoBooleanLabel(probe.pkce_s256_supported)} />
            <MetricTile label="Token" value={localoTokenPresenceLabel(probe.access_token_present)} />
          </div>
          <div className="mt-4 grid gap-3 xl:grid-cols-3">
            {data.sections.map((section) => (
              <article key={section.id} className="rounded-md border border-line p-3">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold">{section.title}</h3>
                  <span className="rounded-md border border-line px-2 py-1 text-xs text-slate-600">
                    {localoSectionStatusLabel(section.status)}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{section.summary}</p>
                <p className="mt-2 text-xs leading-5 text-slate-600">{section.next_step}</p>
              </article>
            ))}
          </div>
        </>
      ) : null}
      {data.visibility_fact_count === 0 ? (
        <BlockerNotice message="Brak Localo ranking/GBP/competitor facts. Ten ekran celowo blokuje lokalne rekomendacje marketingowe." />
      ) : null}
    </section>
  );
}

function localoDecisionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  return status;
}

function localoSectionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  if (status === "missing") return "brak facts";
  return status;
}

function localoDecisionTypeLabel(value: string) {
  const labels: Record<string, string> = {
    access_ready_wait_for_visibility_facts: "status źródła",
    fix_access: "napraw dostęp",
    review_local_visibility: "przejrzyj widoczność",
    block_visibility_claims: "blokada claimów"
  };
  return labels[value] ?? value;
}

function localoConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function localoRefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  return status;
}

function localoAccessStatusLabel(status: string) {
  if (status === "access_ready") return "access działa";
  if (status === "access_blocked") return "access zablokowany";
  return "access niepewny";
}

function localoBooleanLabel(value: boolean | null | undefined) {
  if (value === true) return "tak";
  if (value === false) return "nie";
  return "brak";
}

function localoTokenPresenceLabel(value: boolean | null | undefined) {
  if (value === true) return "obecny";
  if (value === false) return "brak";
  return "brak danych";
}

function localoAllowedEvidenceLabel(value: string) {
  const labels: Record<string, string> = {
    access_token_presence: "obecność tokenu",
    competitor_visibility: "widoczność konkurencji",
    gbp_visibility: "widoczność GBP",
    local_rankings: "rankingi lokalne",
    mcp_initialize: "potwierdzenie dostępu adaptera",
    oauth_metadata: "metadane autoryzacji",
    place_inventory: "lista lokalizacji",
    reviews: "opinie"
  };
  return labels[value] ?? value;
}

function localoMissingContractLabel(value: string) {
  const labels: Record<string, string> = {
    competitor_visibility: "widoczność konkurencji",
    gbp_visibility: "widoczność GBP",
    local_rankings: "rankingi lokalne",
    local_tasks: "zadania lokalne",
    mcp_initialize: "MCP initialize",
    place_inventory: "lista lokalizacji",
    reviews: "opinie"
  };
  return labels[value] ?? value;
}

function localoBlockedClaimLabel(value: string) {
  const labels: Record<string, string> = {
    "competitor visibility": "widoczność konkurencji",
    "GBP performance": "wyniki GBP",
    "GBP post published": "publikacja posta GBP",
    "GBP write": "zmiana GBP",
    "local ranking": "pozycje lokalne",
    "local task completed": "wykonanie zadania lokalnego",
    "local visibility uplift": "wzrost widoczności lokalnej",
    "profile edit applied": "zmiana profilu",
    "review velocity": "tempo opinii",
    "visibility uplift guaranteed": "gwarancja wzrostu widoczności"
  };
  return labels[value] ?? value;
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
