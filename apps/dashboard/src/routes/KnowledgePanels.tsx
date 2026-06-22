import {
  KnowledgeCard,
  KnowledgeOperatingMapResponse,
  MarketingPlaybook
} from "../lib/api";
import { BlockerNotice, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";

export function KnowledgeCardList({ cards }: { cards: KnowledgeCard[] }) {
  if (cards.length === 0) {
    return <p className="text-sm text-slate-600">No compiled knowledge cards yet.</p>;
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {cards.map((card) => (
        <article key={card.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{card.title}</h3>
              <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                {card.card_type} / {card.source_type}
              </p>
            </div>
            <StatusBadge value={`confidence ${Math.round(card.confidence * 100)}%`} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{card.summary}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <div>Source: {card.source_url_or_path}</div>
            <div>Lineage: {card.source_lineage.slice(0, 4).join(", ")}</div>
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
          <h3 className="text-sm font-semibold">{playbook.title}</h3>
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
            <div>Skill: {binding.skill_id ?? "brak"}</div>
            <div>Źródła: {binding.source_connectors.join(", ") || "brak"}</div>
            <div>Dowody: {binding.evidence_ids.length || "brak"}</div>
            <div>ActionObjecty: {binding.action_ids.length || "brak"}</div>
            <div>Karty wiedzy: {binding.knowledge_card_ids.join(", ") || "brak"}</div>
            <div>Playbooki: {binding.playbook_ids.join(", ") || "brak"}</div>
            <div>Reguły: {binding.expert_rule_ids.join(", ") || "brak"}</div>
            <div>Wymagane dowody: {binding.required_evidence.slice(0, 4).join(", ") || "brak"}</div>
            <div>Brakujące kontrakty: {binding.missing_contracts.join(", ") || "brak"}</div>
          </div>
          {binding.blocked_claims.length > 0 ? (
            <p className="mt-3 text-xs text-slate-600">
              Zablokowane claimy: {binding.blocked_claims.slice(0, 4).join(", ")}
            </p>
          ) : null}
          {binding.source_lineage.length > 0 ? (
            <p className="mt-3 text-xs text-slate-600">
              Lineage: {binding.source_lineage.slice(0, 5).join(", ")}
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}
