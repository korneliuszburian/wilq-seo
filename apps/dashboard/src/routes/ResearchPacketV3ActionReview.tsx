import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  hasReviewableResearchPacketV3PageIdentity,
  isSafeResearchPacketV3OfficialSourceUrl,
  isSafeResearchPacketV3PageUrl,
  ResearchPacketV3PreviewRecordSchema
} from "@wilq/shared-schemas";
import { useState } from "react";

import {
  applyAction,
  confirmAction,
  impactCheckAction,
  previewAction,
  reviewAction,
  validateAction,
  type ActionObject
} from "../lib/api";

type PacketDecision = "accepted" | "rejected";
type DecisionResult =
  | { status: "applied" }
  | { status: "rejected" }
  | { status: "stopped"; stage: string; detail: string };

const OPERATOR = "operator_local_dashboard";

function stopped(stage: string, detail: string): DecisionResult {
  return { status: "stopped", stage, detail };
}

export function ResearchPacketV3ActionReview({ action }: { action: ActionObject }) {
  const packetRecord = ResearchPacketV3PreviewRecordSchema.safeParse(
    action.payload.research_packet_v3_preview
  );
  const record = packetRecord.success ? packetRecord.data : null;
  const exactRecord = record && hasReviewableResearchPacketV3PageIdentity(record) ? record : null;
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const [attested, setAttested] = useState(false);
  const decisionMutation = useMutation({
    mutationFn: async (decision: PacketDecision): Promise<DecisionResult> => {
      if (!exactRecord) {
        return stopped("pakiet", "Brakuje dokładnego adresu strony albo ścieżki kanonicznej.");
      }
      const notes = reason.trim();
      if (!notes || !attested) {
        return stopped("review", "Podaj powód i potwierdź przeczytanie dokładnego pakietu.");
      }
      const reviewRequest = {
        outcome: decision === "accepted" ? "approved_for_prepare" as const : "rejected" as const,
        reviewed_by: OPERATOR,
        notes,
        checked_items: ["reviewed_full_packet"],
        blockers: []
      };
      if (decision === "rejected") {
        await reviewAction(action.id, reviewRequest);
        return { status: "rejected" };
      }

      const validation = await validateAction(action.id);
      if (!validation.valid || validation.status !== "valid") {
        return stopped("sprawdzenie", validation.errors.join(" ") || "WILQ nie zatwierdził akcji.");
      }
      const preview = await previewAction(action.id, {
        requested_by: OPERATOR,
        max_items: 8
      });
      if (preview.status !== "preview_ready" || preview.blockers.length > 0) {
        return stopped("podgląd", preview.blocker_labels.join(" ") || "Podgląd jest zablokowany.");
      }
      const review = await reviewAction(action.id, reviewRequest);
      if (review.status !== "recorded") {
        return stopped("review", "WILQ nie zapisał review dokładnego pakietu.");
      }
      const confirmation = await confirmAction(action.id, {
        confirmed_by: OPERATOR,
        notes,
        preview_acknowledged: true
      });
      if (
        !confirmation.confirmed
        || confirmation.status !== "confirmed"
        || confirmation.blockers.length > 0
      ) {
        return stopped(
          "potwierdzenie",
          confirmation.blocker_labels.join(" ") || "Potwierdzenie jest zablokowane."
        );
      }
      const impact = await impactCheckAction(action.id, {
        checked_by: OPERATOR,
        notes
      });
      if (impact.status !== "checked" || impact.blockers.length > 0) {
        return stopped(
          "kontrola efektu",
          impact.blocker_labels.join(" ") || "Kontrola efektu jest zablokowana."
        );
      }
      const applied = await applyAction(action.id, {
        confirm: true,
        confirmed_by: OPERATOR
      });
      if (!applied.applied || applied.status !== "applied") {
        return stopped("lokalny receipt", applied.errors.join(" ") || "Zapis receipt jest zablokowany.");
      }
      return { status: "applied" };
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["content-workflow"] });
    }
  });

  if (!exactRecord) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
        <section className="rounded-md border border-risk/30 bg-white p-4" role="alert">
          Brakuje dokładnego adresu strony lub ścieżki kanonicznej w tym pakiecie. WILQ zachowuje
          historyczny odczyt, ale blokuje nowy review i lokalny receipt.
        </section>
        <section className="mt-4 rounded-md border border-line bg-white p-4" aria-label="Decyzja pakietu">
          <div className="flex flex-wrap gap-3">
            <button type="button" disabled className="rounded-md bg-action px-4 py-2 font-semibold text-white opacity-60">
              Akceptuję
            </button>
            <button type="button" disabled className="rounded-md border border-risk px-4 py-2 font-semibold text-risk opacity-60">
              Nie akceptuję
            </button>
          </div>
        </section>
      </main>
    );
  }

  const packet = exactRecord.snapshot;
  const decisionAlreadyRecorded =
    action.status === "applied"
    || action.review_gate.last_review_outcome === "rejected"
    || action.review_gate.last_mutation_audit_status === "applied"
    || decisionMutation.data?.status === "rejected"
    || decisionMutation.data?.status === "applied";
  const readyForDecision =
    reason.trim().length > 0
    && attested
    && !decisionMutation.isPending
    && !decisionAlreadyRecorded;

  return (
    <main className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-normal text-ink">
          Przegląd dokładnego pakietu badawczego
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Decyzja dotyczy wyłącznie tego pakietu. Akceptacja zapisze lokalny, niezmienny receipt
          WILQ; nie tworzy, nie aktualizuje ani nie publikuje treści WordPress.
        </p>
      </header>

      <section className="mt-6 rounded-md border border-line bg-white p-4" aria-label="Dokładna strona">
        <h2 className="text-sm font-semibold text-ink">Dokładna strona</h2>
        <a
          className="mt-2 block break-all font-medium text-action underline"
          href={packet.page_url}
          rel="noopener noreferrer"
          target="_blank"
        >
          {packet.page_url}
        </a>
        <p className="mt-1 text-sm text-slate-700">Ścieżka kanoniczna: {packet.canonical_path}</p>
      </section>

      <section className="mt-4 rounded-md border border-line bg-white p-4" aria-label="Kontekst planowania">
        <h2 className="text-sm font-semibold text-ink">Kontekst planowania</h2>
        <dl className="mt-3 grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
          <div><dt className="font-medium text-ink">Czytelnik</dt><dd>{packet.planning_context.target_reader}</dd></div>
          <div><dt className="font-medium text-ink">Problem</dt><dd>{packet.planning_context.buyer_problem}</dd></div>
          <div><dt className="font-medium text-ink">Sygnał do działania</dt><dd>{packet.planning_context.buyer_trigger}</dd></div>
          <div><dt className="font-medium text-ink">Kierunek CTA</dt><dd>{packet.cta_direction}</dd></div>
          {packet.planning_context.search_intent ? (
            <div><dt className="font-medium text-ink">Intencja</dt><dd>{packet.planning_context.search_intent}</dd></div>
          ) : null}
        </dl>
        {packet.demand_evidence_status === "missing" ? (
          <p className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-5 text-slate-700">
            Brak bieżących danych popytowych. Ten pakiet nie zawiera metryk, wierszy GSC ani
            rekomendacji opartej na zapytaniach.
          </p>
        ) : (
          <p className="mt-4 text-sm text-slate-700">
            Pakiet zawiera wyłącznie pokazaną wyżej intencję wyszukiwania; nie udostępnia
            wierszy ani metryk popytu.
          </p>
        )}
        <p className="mt-3 text-sm text-slate-700">Minimalna liczba bloków CTA: {packet.minimum_cta_blocks}</p>
        {packet.required_cta_patterns.length > 0 ? (
          <p className="text-sm text-slate-700">Wymagane wzorce CTA: {packet.required_cta_patterns.join(", ")}</p>
        ) : null}
      </section>

      <section className="mt-4 rounded-md border border-line bg-white p-4" aria-label="Oficjalne fakty">
        <h2 className="text-sm font-semibold text-ink">Zatwierdzone fakty z oficjalnych źródeł</h2>
        <ol className="mt-3 space-y-3">
          {packet.selected_facts.map((fact) => {
            const linkedRequirements = packet.legal_requirements.filter((requirement) => (
              requirement.source_fact_ids.includes(fact.source_fact_id)
            ));
            const safeSource = isSafeResearchPacketV3OfficialSourceUrl(fact.source_reference);
            return (
              <li key={fact.source_fact_id} className="rounded-md border border-line bg-slate-50 p-3 text-sm text-slate-700">
                <p className="whitespace-pre-wrap break-words">{fact.text}</p>
                {safeSource ? (
                  <a
                    className="mt-2 inline-block break-all font-medium text-action underline"
                    href={fact.source_reference}
                    rel="noopener noreferrer"
                    target="_blank"
                  >
                    Otwórz oficjalne źródło: {fact.source_reference}
                  </a>
                ) : (
                  <p className="mt-2 text-risk">WILQ nie może bezpiecznie otworzyć referencji źródła.</p>
                )}
                <p className="mt-2">Aktualność źródła: {fact.freshness_date}</p>
                <p className="mt-1 font-medium text-ink">Powiązane wymagania prawne</p>
                {linkedRequirements.length > 0 ? (
                  <ul className="mt-1 list-disc space-y-1 pl-5">
                    {linkedRequirements.map((requirement) => <li key={requirement.requirement_id}>{requirement.label}</li>)}
                  </ul>
                ) : (
                  <p className="mt-1 text-risk">Brakuje powiązanego wymagania w dokładnym pakiecie.</p>
                )}
              </li>
            );
          })}
        </ol>
      </section>

      <section className="mt-4 rounded-md border border-line bg-white p-4" aria-label="Linki wewnętrzne">
        <h2 className="text-sm font-semibold text-ink">Linki wewnętrzne</h2>
        <ul className="mt-3 space-y-2 text-sm text-slate-700">
          {packet.internal_links.map((link) => (
            <li key={link.target_url}>
              <span className="font-medium">{link.anchor_hint}: </span>
              {isSafeResearchPacketV3PageUrl(link.target_url) ? (
                <a href={link.target_url} rel="noopener noreferrer" target="_blank" className="break-all text-action underline">
                  {link.target_url}
                </a>
              ) : (
                <span className="text-risk">WILQ blokuje niebezpieczny adres linku.</span>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-6 rounded-md border border-action/30 bg-surface p-4" aria-label="Decyzja pakietu">
        <h2 className="text-sm font-semibold text-ink">Twoja decyzja</h2>
        <label className="mt-3 block text-sm font-medium text-ink" htmlFor="research-packet-v3-reason">
          Powód decyzji
        </label>
        <textarea
          id="research-packet-v3-reason"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          maxLength={2000}
          className="mt-1 min-h-24 w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink"
          required
        />
        <label className="mt-3 flex items-start gap-2 text-sm leading-5 text-slate-700">
          <input
            type="checkbox"
            checked={attested}
            onChange={(event) => setAttested(event.target.checked)}
            className="mt-0.5"
          />
          <span>Przeczytałem dokładny pakiet, fakty, źródła, wymagania prawne i kierunek CTA.</span>
        </label>
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => decisionMutation.mutate("accepted")}
            disabled={!readyForDecision}
            className="rounded-md bg-action px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {decisionMutation.isPending ? "Zapisuję…" : "Akceptuję"}
          </button>
          <button
            type="button"
            onClick={() => decisionMutation.mutate("rejected")}
            disabled={!readyForDecision}
            className="rounded-md border border-risk px-4 py-2 font-semibold text-risk disabled:cursor-not-allowed disabled:opacity-60"
          >
            Nie akceptuję
          </button>
        </div>
        <DecisionResultPanel result={decisionMutation.data} error={decisionMutation.error} />
        {!decisionMutation.data && decisionAlreadyRecorded ? (
          <p className="mt-3 text-sm text-slate-700" role="status">
            {action.review_gate.last_review_outcome === "rejected"
              ? "Dla tego pakietu zapisano już odrzucenie. Nie można ponowić decyzji."
              : "Dla tego pakietu zapisano już lokalny receipt. Nie można ponowić decyzji."}
          </p>
        ) : null}
      </section>
    </main>
  );
}

function DecisionResultPanel({ result, error }: { result: DecisionResult | undefined; error: unknown }) {
  if (error instanceof Error) {
    return <p className="mt-3 text-sm text-risk" role="alert">WILQ zatrzymał decyzję: {error.message}</p>;
  }
  if (!result) return null;
  if (result.status === "applied") {
    return <p className="mt-3 text-sm text-action" role="status">Lokalny receipt pakietu został zapisany. WordPress pozostaje bez zmian.</p>;
  }
  if (result.status === "rejected") {
    return <p className="mt-3 text-sm text-slate-700" role="status">Zapisano wyłącznie odrzucenie pakietu.</p>;
  }
  return <p className="mt-3 text-sm text-risk" role="alert">Zatrzymano na etapie: {result.stage}. {result.detail}</p>;
}
