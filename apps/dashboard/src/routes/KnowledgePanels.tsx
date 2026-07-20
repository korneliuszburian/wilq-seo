import { useState } from "react";

import {
  KnowledgeCard,
  KnowledgeOperatingMapResponse,
  KnowledgeSourceFactView,
  KnowledgeSourceMaterialReadiness,
  KnowledgeSourceMaterialView,
  MarketingPlaybook
} from "../lib/api";
import { BlockerNotice, LabelChipRow, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";

export function KnowledgeDecisionImpactPanel({ map }: { map: KnowledgeOperatingMapResponse }) {
  const [showMoreDecisions, setShowMoreDecisions] = useState(false);

  if (map.bindings.length === 0) {
    return (
      <BlockerNotice message="Brak powiązań wiedzy z decyzjami. WILQ nie powinien używać wiedzy, której nie da się połączyć z dowodami, źródłami danych i konkretnym krokiem." />
    );
  }

  const primaryBinding = map.bindings[0];
  const secondaryBindings = map.bindings.slice(1, 5);

  return (
    <div className="grid gap-4">
      <article className="rounded-md border border-action/30 bg-action/5 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-normal text-action">
              Najważniejsza decyzja z wiedzy
            </div>
            <h3 className="mt-1 text-lg font-semibold tracking-normal text-ink">
              {primaryBinding.title}
            </h3>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
              {primaryBinding.summary}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge value={primaryBinding.status} label={primaryBinding.status_label} />
            <StatusBadge value={primaryBinding.risk} label={primaryBinding.risk_label} />
          </div>
        </div>
        <div className="mt-4 rounded-md border border-line bg-white p-3 text-sm leading-6 text-ink">
          <div className="font-semibold">Następny krok</div>
          <p>{primaryBinding.next_step}</p>
        </div>
        <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-3">
          <div>Dowody: {primaryBinding.evidence_summary_label}</div>
          <div>Źródła danych: {primaryBinding.source_connector_summary_label}</div>
          <div>Akcje do sprawdzenia: {primaryBinding.action_summary_label}</div>
        </div>
        {primaryBinding.has_blocked_claims ? (
          <p className="mt-3 text-xs leading-5 text-slate-600">
            Zakazane obietnice: {primaryBinding.blocked_claim_count_summary_label}
          </p>
        ) : null}
      </article>
      <div className="grid gap-2 text-center text-xs sm:grid-cols-4">
        <MetricTile label="Decyzje z wiedzą" value={map.binding_count} />
        <MetricTile label="Blokady" value={map.blocked_binding_summary_label} />
        <MetricTile label="Brakujące dane" value={map.missing_contract_summary_label} />
        <MetricTile label="Zakazane obietnice" value={map.blocked_claim_count_summary_label} />
      </div>
      {secondaryBindings.length > 0 ? (
        <div>
          <button
            type="button"
            className="min-h-9 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:border-action hover:text-action"
            onClick={() => setShowMoreDecisions((value) => !value)}
          >
            {showMoreDecisions
              ? "Ukryj pozostałe decyzje z wiedzy"
              : `Pokaż pozostałe decyzje z wiedzy (${secondaryBindings.length})`}
          </button>
          {showMoreDecisions ? (
            <div className="mt-3 grid gap-3 xl:grid-cols-2">
              {secondaryBindings.map((binding) => (
                <KnowledgeImpactDecisionCard key={binding.id} binding={binding} />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function KnowledgeCardList({ cards }: { cards: KnowledgeCard[] }) {
  const [showAll, setShowAll] = useState(false);

  if (cards.length === 0) {
    return (
      <p className="text-sm text-slate-600">
        Nie ma skompilowanych kart wiedzy; WILQ nie powinien używać wiedzy bez źródeł i przeglądu.
      </p>
    );
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

export function KnowledgeSourceFactList({ facts }: { facts: KnowledgeSourceFactView[] }) {
  const [showAll, setShowAll] = useState(false);
  if (facts.length === 0) {
    return <BlockerNotice message="Nie ma jeszcze zdeklarowanych faktów ze źródeł Ekologusa. Nie pokazujemy zastępczych tez." />;
  }
  const visible = showAll ? facts : facts.slice(0, 6);
  return (
    <div className="grid gap-3">
      <div className="rounded-xl border border-action/20 bg-action/5 p-4 text-sm leading-6 text-slate-700">
        To są fakty wyciągnięte z realnych materiałów Ekologusa: publicznych stron oraz zredagowanych materiałów wewnętrznych. Status „review required” oznacza, że fakt nie jest jeszcze wiedzą produkcyjną.
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        {visible.map((fact) => (
          <article key={fact.source_id} className="rounded-xl border border-line bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-action">{fact.scope} · {fact.source_type === "public_site" ? "publiczna strona" : "materiał wewnętrzny"}</p>
                <h3 className="mt-1 text-sm font-semibold text-ink">{fact.target_card_title}</h3>
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${fact.review_status === "approved" ? "bg-emerald-50 text-emerald-700" : "bg-wait/10 text-wait"}`}>{fact.review_status === "approved" ? "zatwierdzony fakt" : "wymaga review"}</span>
                <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${fact.generation_status === "eligible" ? "bg-emerald-50 text-emerald-700" : "bg-risk/10 text-risk"}`}>{fact.generation_status === "eligible" ? "może zasilić draft" : "zablokowany dla draftu"}</span>
              </div>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{fact.extracted_fact}</p>
            <div className="mt-3 grid gap-1 text-xs text-slate-500">
              <span>Źródło: {fact.source_url_or_path}</span>
              <span>Świeżość: {fact.freshness_date} · pewność {Math.round(fact.confidence * 100)}%</span>
              <span>Evidence: {fact.evidence_ids.length ? fact.evidence_ids.join(", ") : "brak — nie używaj jako dowodu"}</span>
            </div>
            {fact.blocked_claims.length ? <p className="mt-3 rounded-md bg-risk/5 p-2 text-xs leading-5 text-risk">Nie używaj bez review: {fact.blocked_claims.join(" · ")}</p> : null}
          </article>
        ))}
      </div>
      {facts.length > 6 ? <button type="button" className="min-h-9 w-fit rounded-md border border-line bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:border-action hover:text-action" onClick={() => setShowAll((value) => !value)}>{showAll ? "Pokaż mniej faktów" : `Pokaż wszystkie fakty (${facts.length})`}</button> : null}
    </div>
  );
}

export function KnowledgeSourceMaterialSummary({ materials }: { materials: KnowledgeSourceMaterialView[] }) {
  const [showAll, setShowAll] = useState(false);
  if (!materials.length) return null;
  const visible = showAll ? materials : materials.slice(0, 5);
  return (
    <div className="mt-4 rounded-xl border border-line bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-action">Korpus źródłowy</p>
          <h3 className="mt-1 text-sm font-semibold text-ink">{materials.length} materiałów w manifeście Ekologusa</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">Manifest i hashe są znane. Tekst pozostaje poza generowaniem do czasu redakcji i review.</p>
        </div>
        <span className="rounded-full bg-wait/10 px-2.5 py-1 text-[11px] font-semibold text-wait">
          {materials.every((material) => material.import_status === "imported")
            ? "zaimportowane"
            : `${materials.filter((material) => material.import_status !== "imported").length} oczekuje`}
        </span>
      </div>
      <div className="mt-3 grid gap-2 xl:grid-cols-2">
        {visible.map((material) => (
          <div key={material.source_id} className="rounded-md border border-line bg-slate-50/70 p-3 text-xs">
            <div className="font-semibold text-ink">{material.title}</div>
            <div className="mt-1 text-slate-600">{material.kind} · {material.word_count} słów · {material.file_name}</div>
            <div className="mt-1 text-slate-500">SHA prefix: {material.digest_prefix} · {material.privacy_class}</div>
          </div>
        ))}
      </div>
      {materials.length > 5 ? <button type="button" className="mt-3 min-h-9 rounded-md border border-line bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:border-action hover:text-action" onClick={() => setShowAll((value) => !value)}>{showAll ? "Pokaż mniej materiałów" : `Pokaż wszystkie materiały (${materials.length})`}</button> : null}
    </div>
  );
}

export function KnowledgeSourceMaterialReadinessBanner({
  readiness
}: {
  readiness: KnowledgeSourceMaterialReadiness | undefined;
}) {
  if (!readiness) return null;
  return (
    <div className="mt-4 rounded-md border border-wait/30 bg-wait/5 p-3 text-sm" aria-live="polite">
      <div className="font-semibold text-ink">
        Korpus źródłowy: {readiness.ready_for_generation ? "gotowy" : "zablokowany"}
      </div>
      <div className="mt-1 text-xs text-slate-600">
        {readiness.imported_count}/{readiness.total_count} materiałów zaimportowanych · {readiness.import_pending_count} oczekuje na import · {readiness.excerpt_review_required_count} wymaga review excerptów
      </div>
      {readiness.blocker ? <div className="mt-2 text-xs text-wait">{readiness.blocker}</div> : null}
      {(readiness.pending_materials ?? []).length > 0 ? (
        <div className="mt-2 text-xs text-slate-600">
          Czekają konkretne materiały: {(readiness.pending_materials ?? []).map((material) => material.title).join(" · ")}
        </div>
      ) : null}
      <div className="mt-2 text-xs text-slate-600">Następny krok: {readiness.next_step}</div>
    </div>
  );
}

export function PlaybookList({ playbooks }: { playbooks: MarketingPlaybook[] }) {
  const [showAll, setShowAll] = useState(false);

  if (playbooks.length === 0) {
    return (
      <p className="text-sm text-slate-600">
        Nie ma skompilowanych zasad pracy; WILQ nie powinien zamieniać ich w rekomendacje.
      </p>
    );
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

function KnowledgeImpactDecisionCard({ binding }: { binding: KnowledgeDecisionBinding }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
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
  );
}

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
