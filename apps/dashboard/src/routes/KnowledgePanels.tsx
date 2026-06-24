import {
  KnowledgeCard,
  KnowledgeOperatingMapResponse,
  MarketingPlaybook
} from "../lib/api";
import { BlockerNotice, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";

export function KnowledgeCardList({ cards }: { cards: KnowledgeCard[] }) {
  if (cards.length === 0) {
    return <p className="text-sm text-slate-600">Brak skompilowanych kart wiedzy.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {cards.map((card) => (
        <article key={card.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{knowledgeCardDisplayTitle(card)}</h3>
              <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                {knowledgeCardTypeLabel(card.card_type)} / {knowledgeSourceTypeLabel(card.source_type)}
              </p>
            </div>
            <StatusBadge value={`confidence ${Math.round(card.confidence * 100)}%`} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{card.summary}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <div>Źródło: {card.source_url_or_path}</div>
            <div>Ślady źródłowe: {formatCount(card.source_lineage.length, "element")}</div>
          </div>
        </article>
      ))}
    </div>
  );
}

export function PlaybookList({ playbooks }: { playbooks: MarketingPlaybook[] }) {
  if (playbooks.length === 0) {
    return <p className="text-sm text-slate-600">Brak maszynowych playbooków.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {playbooks.map((playbook) => (
        <article key={playbook.id} className="rounded-md border border-line bg-white p-4">
          <h3 className="text-sm font-semibold">{playbookDisplayTitle(playbook)}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">{playbook.output_contract}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Wymagane dowody: {playbook.required_evidence.slice(0, 4).join(", ")}</div>
            <div>Akcje: {playbook.maps_to_action_types.slice(0, 3).join(", ")}</div>
          </div>
        </article>
      ))}
    </div>
  );
}

export function KnowledgeOperatingMapPanel({ map }: { map: KnowledgeOperatingMapResponse }) {
  if (map.bindings.length === 0) {
    return (
      <BlockerNotice message="Brak mapy wiedzy do decyzji. WILQ nie powinien pokazywać reguł bez powiązania z evidence i workflowem." />
    );
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {map.bindings.map((binding) => (
        <article key={binding.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{binding.title}</h3>
              <p className="mt-1 break-words text-xs text-slate-500">
                {binding.id} / {binding.route}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusBadge value={binding.status} />
              <StatusBadge value={binding.risk} />
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
          <p className="mt-3 text-sm font-medium text-ink">{binding.next_step}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Skill: {binding.skill_id ? "dostępny" : "brak"}</div>
            <div>Źródła: {binding.source_connectors.join(", ") || "brak"}</div>
            <div>Dowody: {formatCount(binding.evidence_ids.length, "ID")}</div>
            <div>Akcje: {formatCount(binding.action_ids.length, "ID")}</div>
            <div>Karty wiedzy: {binding.knowledge_card_ids.length}</div>
            <div>Playbooki: {binding.playbook_ids.length}</div>
            <div>Reguły eksperckie: {binding.expert_rule_ids.length}</div>
            <div>Wymagane dowody: {binding.required_evidence.length}</div>
            <div>Brakujące kontrakty: {binding.missing_contracts.length}</div>
          </div>
          {binding.blocked_claims.length > 0 ? (
            <p className="mt-3 text-xs text-slate-600">
              Zablokowane claimy: {binding.blocked_claims.slice(0, 4).join(", ")}
            </p>
          ) : null}
          {binding.source_lineage.length > 0 ? (
            <p className="mt-3 text-xs text-slate-600">
              Ślady źródłowe: {formatCount(binding.source_lineage.length, "element")}
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function formatCount(count: number, unit: string) {
  return count > 0 ? `${count} ${unit}` : "brak";
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
    marketing_playbook: "playbook marketingowy",
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
