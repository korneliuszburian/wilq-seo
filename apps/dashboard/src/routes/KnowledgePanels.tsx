import { useState } from "react";

import {
  KnowledgeCard,
  KnowledgeOperatingMapResponse,
  MarketingPlaybook
} from "../lib/api";
import { BlockerNotice, LabelChipRow, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";

export function KnowledgeDecisionImpactPanel({ map }: { map: KnowledgeOperatingMapResponse }) {
  if (map.bindings.length === 0) {
    return (
      <BlockerNotice message="Brak powiązań wiedzy z decyzjami. WILQ nie powinien używać wiedzy, której nie da się połączyć z dowodami, źródłami danych i konkretnym krokiem." />
    );
  }

  const topBindings = map.bindings.slice(0, 5);

  return (
    <div className="grid gap-4">
      <div className="grid gap-2 text-center text-xs sm:grid-cols-4">
        <MetricTile label="Decyzje z wiedzą" value={map.binding_count} />
        <MetricTile label="Blokady" value={map.blocked_binding_summary_label} />
        <MetricTile label="Brakujące dane" value={map.missing_contract_summary_label} />
        <MetricTile label="Zakazane obietnice" value={map.blocked_claim_count_summary_label} />
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        {topBindings.map((binding) => (
          <article key={binding.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">{binding.title}</h3>
                <p className="mt-1 text-xs text-slate-500">{binding.route_label || "powiązany widok"}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge value={binding.status} label={binding.status_label} />
                <StatusBadge value={binding.risk} label={binding.risk_label} />
              </div>
            </div>
            <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-wait">
              <div className="font-semibold">Co zrobić dalej</div>
              <p>{binding.next_step}</p>
            </div>
            <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-3">
              <div>Dowody: {binding.evidence_summary_label}</div>
              <div>Źródła danych: {binding.source_connector_summary_label}</div>
              <div>Akcje do sprawdzenia: {binding.action_summary_label}</div>
            </div>
            {binding.has_blocked_claims ? (
              <p className="mt-3 text-xs leading-5 text-slate-600">
                Zakazane obietnice: {binding.blocked_claim_count_summary_label}
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
      <BlockerNotice message="Brak mapy wiedzy do decyzji. WILQ nie powinien pokazywać reguł bez powiązania z dowodami i procesem pracy." />
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

  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{binding.title}</h3>
          <p className="mt-1 text-xs text-slate-500">
            Widok: {binding.route_label || "powiązany widok"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge value={binding.status} label={binding.status_label} />
          <StatusBadge value={binding.risk} label={binding.risk_label} />
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
        <div>Dowody: {binding.evidence_summary_label}</div>
        <div>Źródła danych: {binding.source_connector_summary_label}</div>
        <div>Wiedza użyta w decyzji: {binding.knowledge_summary_label}</div>
        <div>Braki: {binding.missing_contract_summary_label}</div>
      </div>
      {binding.has_blocked_claims ? (
        <p className="mt-3 text-xs text-slate-600">
          Zablokowane obietnice: {binding.blocked_claim_count_summary_label}
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
          <div>Źródła: {binding.source_connector_summary_label}</div>
          <div>
            Dowody:{" "}
            {binding.evidence_summary_label}
          </div>
          <div>
            Akcje:{" "}
            {binding.action_summary_label}
          </div>
          <div>Wiedza użyta: {binding.knowledge_summary_label}</div>
          <div>Wymagane dowody: {binding.required_evidence_summary_label}</div>
          <div>Brakujące dane: {binding.missing_contract_detail_label}</div>
          <div>Zakazane obietnice: {binding.blocked_claim_summary_label}</div>
          <div>Ślady źródłowe: {binding.source_lineage_summary_label}</div>
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
          <h3 className="text-sm font-semibold">{card.display_title}</h3>
          <LabelChipRow
            className="mt-2"
            chips={[
              { label: "Typ", value: card.card_type_label },
              { label: "Źródło", value: card.source_type_label }
            ]}
          />
        </div>
        <span className="inline-flex min-h-7 items-center rounded border border-line bg-white px-2 text-xs font-medium text-ink">
          Pewność {Math.round(card.confidence * 100)}%
        </span>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <div>Źródła wiedzy: {card.source_lineage_summary_label}</div>
        <div>Źródło: {card.source_type_label}</div>
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
          <p className="mt-2">Ślady źródłowe: {card.source_lineage_summary_label}</p>
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
      <h3 className="text-sm font-semibold">{playbook.display_title}</h3>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <div>Wymagane dowody: {playbook.required_evidence_summary_label}</div>
        <div>Akcje do sprawdzenia: {playbook.mapped_action_type_summary_label}</div>
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
          <p className="mt-2">Wymagane dowody: {playbook.required_evidence_summary_label}</p>
          <p className="mt-2">
            Akcje do sprawdzenia: {playbook.mapped_action_type_summary_label}
          </p>
        </div>
      ) : null}
    </article>
  );
}
