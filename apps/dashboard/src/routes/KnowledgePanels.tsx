import { useState } from "react";

import {
  KnowledgeCard,
  KnowledgeOperatingMapResponse,
  MarketingPlaybook
} from "../lib/api";
import { BlockerNotice, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";

export function KnowledgeDecisionImpactPanel({ map }: { map: KnowledgeOperatingMapResponse }) {
  if (map.bindings.length === 0) {
    return (
      <BlockerNotice message="Brak powiązań wiedzy z decyzjami. WILQ nie powinien używać wiedzy, której nie da się połączyć z dowodami, źródłami danych i konkretnym krokiem." />
    );
  }

  const topBindings = map.bindings.slice(0, 5);
  const blockedCount = map.bindings.filter((binding) => binding.status === "blocked").length;
  const missingContractCount = map.bindings.reduce(
    (total, binding) => total + binding.missing_contracts.length,
    0
  );
  const blockedClaimCount = map.bindings.reduce(
    (total, binding) => total + binding.blocked_claims.length,
    0
  );

  return (
    <div className="grid gap-4">
      <div className="grid gap-2 text-center text-xs sm:grid-cols-4">
        <MetricTile label="Decyzje z wiedzą" value={map.binding_count} />
        <MetricTile label="Blokady" value={blockedCount} />
        <MetricTile label="Brakujące kontrakty" value={missingContractCount} />
        <MetricTile label="Zakazane obietnice" value={blockedClaimCount} />
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        {topBindings.map((binding) => (
          <article key={binding.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">{binding.title}</h3>
                <p className="mt-1 text-xs text-slate-500">{routeDisplayLabel(binding.route)}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge value={binding.status} />
                <StatusBadge value={binding.risk} />
              </div>
            </div>
            <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-wait">
              <div className="font-semibold">Co zrobić dalej</div>
              <p>{binding.next_step}</p>
            </div>
            <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-3">
              <div>Dowody: {binding.evidence_ids.length}</div>
              <div>
                Źródła danych:{" "}
                {formatPolishCount(binding.source_connectors.length, "źródło", "źródła", "źródeł")}
              </div>
              <div>
                Akcje do sprawdzenia:{" "}
                {formatPolishCount(binding.action_ids.length, "akcja", "akcje", "akcji")}
              </div>
            </div>
            {binding.blocked_claims.length > 0 ? (
              <p className="mt-3 text-xs leading-5 text-slate-600">
                Zakazane obietnice: {binding.blocked_claims.length}
              </p>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}

export function KnowledgeCardList({ cards }: { cards: KnowledgeCard[] }) {
  const [showAll, setShowAll] = useState(false);

  if (cards.length === 0) {
    return <p className="text-sm text-slate-600">Brak skompilowanych kart wiedzy.</p>;
  }

  const visibleCards = showAll ? cards : cards.slice(0, 4);
  const hiddenCount = Math.max(cards.length - visibleCards.length, 0);

  return (
    <div className="grid gap-3">
      <div className="grid gap-3 xl:grid-cols-2">
        {visibleCards.map((card) => (
          <KnowledgeCardItem key={card.id} card={card} />
        ))}
      </div>
      {hiddenCount > 0 || showAll ? (
        <button
          type="button"
          className="min-h-9 w-fit rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:border-action hover:text-action"
          onClick={() => setShowAll((value) => !value)}
        >
          {showAll ? "Pokaż mniej kart" : `Pokaż wszystkie karty (${cards.length})`}
        </button>
      ) : null}
    </div>
  );
}

export function PlaybookList({ playbooks }: { playbooks: MarketingPlaybook[] }) {
  const [showAll, setShowAll] = useState(false);

  if (playbooks.length === 0) {
    return <p className="text-sm text-slate-600">Brak skompilowanych zasad pracy.</p>;
  }

  const visiblePlaybooks = showAll ? playbooks : playbooks.slice(0, 4);
  const hiddenCount = Math.max(playbooks.length - visiblePlaybooks.length, 0);

  return (
    <div className="grid gap-3">
      <div className="grid gap-3 xl:grid-cols-2">
        {visiblePlaybooks.map((playbook) => (
          <PlaybookItem key={playbook.id} playbook={playbook} />
        ))}
      </div>
      {hiddenCount > 0 || showAll ? (
        <button
          type="button"
          className="min-h-9 w-fit rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:border-action hover:text-action"
          onClick={() => setShowAll((value) => !value)}
        >
          {showAll ? "Pokaż mniej zasad" : `Pokaż wszystkie zasady (${playbooks.length})`}
        </button>
      ) : null}
    </div>
  );
}

export function KnowledgeOperatingMapPanel({ map }: { map: KnowledgeOperatingMapResponse }) {
  const [showAll, setShowAll] = useState(false);

  if (map.bindings.length === 0) {
    return (
      <BlockerNotice message="Brak mapy wiedzy do decyzji. WILQ nie powinien pokazywać reguł bez powiązania z evidence i workflowem." />
    );
  }

  const visibleBindings = showAll ? map.bindings : map.bindings.slice(0, 4);
  const hiddenCount = Math.max(map.bindings.length - visibleBindings.length, 0);

  return (
    <div className="grid gap-3">
      <div className="grid gap-3 xl:grid-cols-2">
        {visibleBindings.map((binding) => (
          <KnowledgeDecisionBindingCard key={binding.id} binding={binding} />
        ))}
      </div>
      {hiddenCount > 0 || showAll ? (
        <button
          type="button"
          className="min-h-9 w-fit rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:border-action hover:text-action"
          onClick={() => setShowAll((value) => !value)}
        >
          {showAll ? "Pokaż mniej powiązań" : `Pokaż wszystkie powiązania (${map.bindings.length})`}
        </button>
      ) : null}
    </div>
  );
}

type KnowledgeDecisionBinding = KnowledgeOperatingMapResponse["bindings"][number];

function KnowledgeDecisionBindingCard({ binding }: { binding: KnowledgeDecisionBinding }) {
  const [showDetails, setShowDetails] = useState(false);
  const knowledgeCount =
    binding.knowledge_card_ids.length + binding.playbook_ids.length + binding.expert_rule_ids.length;

  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{binding.title}</h3>
          <p className="mt-1 text-xs text-slate-500">Widok: {routeDisplayLabel(binding.route)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge value={knowledgeStatusLabel(binding.status)} />
          <StatusBadge value={knowledgeRiskLabel(binding.risk)} />
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{binding.summary}</p>
      {Object.keys(binding.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-700 sm:grid-cols-3">
          {Object.entries(binding.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${binding.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-3 rounded-md border border-action/20 bg-action/5 p-3 text-sm leading-6 text-ink">
        <div className="font-semibold">Następny krok</div>
        <p>{binding.next_step}</p>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <div>Dowody: {formatCount(binding.evidence_ids.length, "dowód")}</div>
        <div>Źródła danych: {formatCount(binding.source_connectors.length, "źródło")}</div>
        <div>Wiedza użyta w decyzji: {formatCount(knowledgeCount, "element")}</div>
        <div>Braki: {binding.missing_contracts.length > 0 ? binding.missing_contracts.length : "brak"}</div>
      </div>
      {binding.blocked_claims.length > 0 ? (
        <p className="mt-3 text-xs text-slate-600">
          Zablokowane obietnice: {formatCount(binding.blocked_claims.length, "pozycja")}
        </p>
      ) : null}
      <button
        type="button"
        className="mt-3 min-h-8 rounded-md border border-line bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:border-action hover:text-action"
        onClick={() => setShowDetails((value) => !value)}
      >
        {showDetails ? "Ukryj szczegóły techniczne" : "Pokaż szczegóły techniczne"}
      </button>
      {showDetails ? (
        <div className="mt-3 grid gap-2 rounded-md border border-line bg-slate-50 p-3 text-xs leading-5 text-slate-600 sm:grid-cols-2">
          <div>Źródła: {binding.source_connectors.join(", ") || "brak"}</div>
          <div>
            Dowody:{" "}
            {formatPolishCount(
              binding.evidence_ids.length,
              "dowód źródłowy",
              "dowody źródłowe",
              "dowodów źródłowych"
            )}
          </div>
          <div>
            Akcje:{" "}
            {formatPolishCount(
              binding.action_ids.length,
              "akcja do sprawdzenia",
              "akcje do sprawdzenia",
              "akcji do sprawdzenia"
            )}
          </div>
          <div>Karty wiedzy: {binding.knowledge_card_ids.length}</div>
          <div>Zasady pracy: {binding.playbook_ids.length}</div>
          <div>Reguły decyzji: {binding.expert_rule_ids.length}</div>
          <div>Wymagane dowody: {binding.required_evidence.length}</div>
          <div>Brakujące kontrakty: {binding.missing_contracts.length}</div>
          <div>Ślady źródłowe: {formatCount(binding.source_lineage.length, "element")}</div>
          <div>Identyfikator: {binding.id}</div>
        </div>
      ) : null}
    </article>
  );
}

function KnowledgeCardItem({ card }: { card: KnowledgeCard }) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{knowledgeCardDisplayTitle(card)}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {knowledgeCardTypeLabel(card.card_type)} / {knowledgeSourceTypeLabel(card.source_type)}
          </p>
        </div>
        <StatusBadge value={`pewność ${Math.round(card.confidence * 100)}%`} />
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <div>Ślady źródłowe: {formatCount(card.source_lineage.length, "element")}</div>
        <div>Źródło: {knowledgeSourceTypeLabel(card.source_type)}</div>
      </div>
      <button
        type="button"
        className="mt-3 min-h-8 rounded-md border border-line bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:border-action hover:text-action"
        onClick={() => setShowDetails((value) => !value)}
      >
        {showDetails ? "Ukryj źródło" : "Pokaż źródło"}
      </button>
      {showDetails ? (
        <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-xs leading-5 text-slate-600">
          <p>Ta karta jest używana tylko jako wsparcie decyzji, gdy ma powiązanie z dowodami i źródłami danych.</p>
          <p className="mt-2 break-words">Plik albo URL: {card.source_url_or_path}</p>
        </div>
      ) : null}
    </article>
  );
}

function PlaybookItem({ playbook }: { playbook: MarketingPlaybook }) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <article className="rounded-md border border-line bg-white p-4">
      <h3 className="text-sm font-semibold">{playbookDisplayTitle(playbook)}</h3>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <div>Wymagane dowody: {formatCount(playbook.required_evidence.length, "element")}</div>
        <div>Akcje do sprawdzenia: {formatCount(playbook.maps_to_action_types.length, "typ")}</div>
      </div>
      <button
        type="button"
        className="mt-3 min-h-8 rounded-md border border-line bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:border-action hover:text-action"
        onClick={() => setShowDetails((value) => !value)}
      >
        {showDetails ? "Ukryj zasady" : "Pokaż zasady"}
      </button>
      {showDetails ? (
        <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-xs leading-5 text-slate-600">
          <p>Ta zasada pracy może wspierać decyzję tylko wtedy, gdy WILQ ma wymagane dowody i listę twierdzeń, których nie wolno używać.</p>
          <p className="mt-2">Wymagane dowody: {formatCount(playbook.required_evidence.length, "element")}</p>
          <p className="mt-2">
            Akcje do sprawdzenia: {formatCount(playbook.maps_to_action_types.length, "typ")}
          </p>
        </div>
      ) : null}
    </article>
  );
}

function formatCount(count: number, unit: string) {
  return count > 0 ? `${count} ${unit}` : "brak";
}

function formatPolishCount(count: number, singular: string, few: string, many: string) {
  if (count === 0) return "brak";
  if (count === 1) return `1 ${singular}`;
  const lastDigit = count % 10;
  const lastTwoDigits = count % 100;
  if (lastDigit >= 2 && lastDigit <= 4 && !(lastTwoDigits >= 12 && lastTwoDigits <= 14)) {
    return `${count} ${few}`;
  }
  return `${count} ${many}`;
}

function routeDisplayLabel(route: string) {
  const labels: Record<string, string> = {
    "/ads-doctor": "Ads Doctor",
    "/content-planner": "Content Planner",
    "/merchant": "Merchant Center",
    "/ga4": "GA4",
    "/localo": "Localo",
    "/command-center": "Command Center"
  };
  return labels[route] ?? "powiązany widok";
}

function knowledgeStatusLabel(value: string) {
  const labels: Record<string, string> = {
    ready: "gotowe",
    partial: "częściowe",
    blocked: "zablokowane",
    review_only: "do sprawdzenia"
  };
  return labels[value] ?? value;
}

function knowledgeRiskLabel(value: string) {
  const labels: Record<string, string> = {
    low: "niskie ryzyko",
    medium: "średnie ryzyko",
    high: "wysokie ryzyko"
  };
  return labels[value] ?? value;
}

function knowledgeCardDisplayTitle(card: KnowledgeCard) {
  return KNOWLEDGE_DISPLAY_LABELS[card.source_id] ?? KNOWLEDGE_DISPLAY_LABELS[card.id] ?? card.title;
}

function playbookDisplayTitle(playbook: MarketingPlaybook) {
  return KNOWLEDGE_DISPLAY_LABELS[playbook.id] ?? playbook.title;
}

function knowledgeCardTypeLabel(value: string) {
  const labels: Record<string, string> = {
    ads_pattern_card: "wzorzec Ads",
    campaign_card: "kampanie",
    competitor_card: "konkurencja",
    content_card: "treści",
    keyword_cluster_card: "klastry słów",
    local_visibility_card: "widoczność lokalna",
    negative_keyword_pattern_card: "wykluczenia",
    service_card: "feed i usługi",
    social_pattern_card: "social",
    voice_rule: "reguła głosu"
  };
  return labels[value] ?? value;
}

function knowledgeSourceTypeLabel(value: string) {
  const labels: Record<string, string> = {
    marketing_playbook: "zasada pracy",
    repo_goal: "reguła projektu"
  };
  return labels[value] ?? value;
}

const KNOWLEDGE_DISPLAY_LABELS: Record<string, string> = {
  card_goal_001_rules: "Zakaz wymyślania metryk",
  google_ads_search_playbook: "Diagnostyka wyszukiwanych haseł Google Ads",
  google_ads_budget_review_playbook: "Przegląd budżetów Google Ads",
  google_ads_demand_gen_playbook: "Gotowość Demand Gen",
  google_ads_pmax_playbook: "Gotowość PMax i sprzedaży produktowej",
  google_ads_negative_keywords_playbook: "Przegląd wykluczeń Google Ads",
  google_ads_custom_segments_playbook: "Segmenty niestandardowe z wyszukiwanych haseł",
  gsc_seo_content_playbook: "Okazje SEO i content z GSC",
  ahrefs_content_gap_playbook: "Luki contentowe i konkurencja z Ahrefs",
  localo_local_seo_playbook: "Widoczność lokalna Localo",
  ga4_behavior_diagnostics_playbook: "Diagnostyka zachowania GA4",
  merchant_feed_optimization_playbook: "Diagnostyka feedu Merchant",
  linkedin_content_playbook: "Publikacje LinkedIn",
  facebook_content_playbook: "Publikacje Facebook",
  wordpress_content_refresh_playbook: "Odświeżanie treści WordPress"
};
