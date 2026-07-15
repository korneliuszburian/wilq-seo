import type {
  ContentWorkItemWordPressDraftExecutionResponse,
  WordPressAuthoringProfile
} from "../lib/api";
import { ContentWorkflowFactTile as FactTile } from "./ContentWorkflowFactTile";
import { WordPressDraftExecutionStatus, WordPressDraftReadbackStatus } from "./WordPressDraftStatus";
import type { WordPressAuthoringProfileQuery, WordPressDraftActivationPacketQuery, WordPressDraftWriteReadinessQuery } from "./contentWorkflowQueries";

type WordPressDraftWorkActions = {
  executionResult: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] | null;
  executionPending: boolean;
  runExecutionDryRun: () => void;
};

type WordPressDraftWorkPanelProps = {
  actions: WordPressDraftWorkActions;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
};

export function WordPressDraftWorkPanel({ actions, authoringProfile, draftActivationPacket, draftWriteReadiness }: WordPressDraftWorkPanelProps) {
  const profile: WordPressAuthoringProfile | null = authoringProfile.data ?? null;
  const readiness = draftWriteReadiness.data;
  const packet = draftActivationPacket.data;
  const isLoading = authoringProfile.isLoading || draftActivationPacket.isLoading || draftWriteReadiness.isLoading;
  if (isLoading) return <section className="mb-6 rounded-md border border-line bg-white p-4"><h2 className="text-sm font-semibold text-ink">Dev draft WordPress</h2><p className="mt-2 text-sm text-slate-600">Sprawdzam dev, ACF i gotowość szkicu.</p></section>;
  if (authoringProfile.error || draftActivationPacket.error || draftWriteReadiness.error) return <section className="mb-6 rounded-md border border-wait/30 bg-wait/10 p-4"><h2 className="text-sm font-semibold text-wait">Dev draft WordPress</h2><p className="mt-2 text-sm leading-6 text-slate-700">Nie udało się odczytać pełnej gotowości dev WordPress. Nie zaczynaj zapisu bez profilu authoringu, paczki szkicu i readiness z WILQ API.</p></section>;
  const latestCreatedExecution = actions.executionResult ?? (packet?.execution_result.status === "created" ? packet.execution_result : null);
  const draftReadback = packet?.draft_readback ?? null;
  const canPreviewDraft = Boolean(packet?.draft_package_ready && packet.handoff_ready && packet.dry_run_ready && packet.execution_blockers.length === 0 && !actions.executionPending);
  const acfLayoutCount = profile?.acf.layouts.length ?? 0;
  const missingReadiness = [...(packet?.activation_missing_readiness_labels ?? []), ...(readiness?.blockers.map((blocker) => blocker.label) ?? [])].slice(0, 5);
  const nextStep = packet?.operator_next_step ?? readiness?.operator_next_step ?? "Najpierw przygotuj review paczki szkicu i zapis audytu w WILQ.";
  return (
    <section className="mb-6 overflow-hidden rounded-md border border-action/25 bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-action/15 bg-blue-50 px-4 py-3"><div><p className="text-xs font-semibold uppercase tracking-normal text-action">Roboczy WordPress</p><h2 className="mt-1 text-base font-semibold text-ink">Dev draft WordPress</h2><p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">Piszemy i układamy szkic na ekologus.dev.proudsite.pl. Publiczna strona pozostaje punktem odniesienia, ale dev nie jest kanonicznym adresem SEO.</p></div><span className="rounded-md bg-wait/10 px-3 py-2 text-sm font-semibold text-wait">zapis przez akcję zablokowany</span></div>
      <div className="grid gap-4 p-4 lg:grid-cols-[1fr_1fr]"><div><div className="grid gap-3 sm:grid-cols-4"><FactTile label="Paczka szkicu" value={packet?.draft_package_ready ? "gotowa" : "brak"} /><FactTile label="Review" value={packet?.human_review_ready ? "gotowe" : "wymagane"} /><FactTile label="ACF" value={acfLayoutCount ? `${acfLayoutCount} layoutów` : "brak odczytu"} /><FactTile label="Publikacja" value="zablokowana" /></div><div className="mt-4 rounded-md border border-line bg-surface p-3"><h3 className="text-sm font-semibold text-ink">Następny krok</h3><p className="mt-2 text-sm leading-6 text-slate-700">{nextStep}</p><div className="mt-4 flex flex-wrap gap-3"><button type="button" onClick={actions.runExecutionDryRun} disabled={!canPreviewDraft} className="inline-flex h-9 items-center rounded-md bg-action px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60">{actions.executionPending ? "Sprawdzam podgląd" : "Sprawdź podgląd draftu"}</button></div>{packet?.handoff_ready ? <p className="mt-2 text-xs leading-5 text-slate-500">Pełny zapis dokładnej wersji wykonasz w widoku Marketer, w kroku „Szkic na devie”.</p> : null}{latestCreatedExecution ? <WordPressDraftExecutionStatus result={latestCreatedExecution} /> : null}{draftReadback ? <WordPressDraftReadbackStatus readback={draftReadback} /> : null}</div></div><div className="rounded-md border border-line bg-white p-3"><h3 className="text-sm font-semibold text-ink">Co blokuje zapis szkicu</h3>{missingReadiness.length > 0 ? <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-700">{missingReadiness.map((label) => <li key={label}>- {label}</li>)}</ul> : <p className="mt-2 text-sm leading-6 text-slate-700">WILQ nie zgłasza brakujących etapów dla podglądu. Zapis nadal idzie przez akcję, review, potwierdzenie i audyt.</p>}<div className="mt-4 flex flex-wrap gap-3"><a href="https://ekologus.dev.proudsite.pl/" target="_blank" rel="noreferrer" className="inline-flex h-9 items-center rounded-md bg-action px-3 text-sm font-semibold text-white">Otwórz dev</a><a href="https://ekologus.dev.proudsite.pl/wp-admin/" target="_blank" rel="noreferrer" className="inline-flex h-9 items-center rounded-md border border-line px-3 text-sm font-semibold text-ink">Otwórz WordPress admin</a></div></div></div>
    </section>
  );
}
