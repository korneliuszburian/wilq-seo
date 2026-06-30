import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock3, FileText, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  buildWorkflowSteps,
  loadContentWorkflowSnapshot,
  type ContentWorkflowSnapshot,
  type WorkflowStep
} from "./contentWorkflowRuntime";

type WorkflowSafetyPanelsProps = {
  data: ContentWorkflowSnapshot;
  draft: ContentWorkflowSnapshot["draftPackage"]["draft_package_result"]["draft_package"];
  handoff: ContentWorkflowSnapshot["wordpressHandoff"]["handoff_result"]["handoff"];
  window: ContentWorkflowSnapshot["measurementWindow"]["measurement_window_result"]["window"];
};

export function ContentWorkflowSurface() {
  const workflow = useQuery({
    queryKey: ["content-workflow", "bdo-control-path"],
    queryFn: loadContentWorkflowSnapshot
  });

  if (workflow.isLoading) return <LoadingBand />;
  if (workflow.error || !workflow.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <div className="rounded-md border border-wait/30 bg-wait/10 p-4 text-sm text-wait">
          Nie udało się odczytać workflow treści z WILQ. Nie pokazujemy decyzji bez kontraktów API.
        </div>
      </main>
    );
  }

  const data = workflow.data;
  const item = data.preflight.item;
  const draft = data.draftPackage.draft_package_result.draft_package;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  const window = data.measurementWindow.measurement_window_result.window;
  const steps = buildWorkflowSteps(data);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <ContentWorkflowHeader topic={item.topic} />
      <WorkflowProofSummary data={data} />
      <WorkflowStepsList steps={steps} />
      <WorkflowSafetyPanels data={data} draft={draft} handoff={handoff} window={window} />
    </main>
  );
}

function ContentWorkflowHeader({ topic }: { topic: string }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">Workflow treści bez slopu</h1>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
          Pierwszy kontrolny tor pokazuje, czy WILQ potrafi przeprowadzić temat od sprawdzenia pisania
          do szkicu WordPress i okna pomiaru bez pomijania bramek.
        </p>
      </div>
      <div className="rounded-md border border-line bg-white px-4 py-3 text-sm">
        <div className="text-xs uppercase tracking-normal text-slate-500">Temat</div>
        <div className="mt-1 font-semibold text-ink">{topic}</div>
      </div>
    </div>
  );
}

function WorkflowProofSummary({ data }: { data: ContentWorkflowSnapshot }) {
  const item = data.preflight.item;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Co WILQ już potwierdził
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Finalny adres pozostaje publicznym adresem Ekologus, podgląd dev jest tylko kontekstem
            projektu, a WordPress nie dostaje publikacji automatycznej.
          </p>
        </div>
        <div className="grid gap-2 text-sm sm:grid-cols-3">
          <FactTile label="Dowody" value={`Dowody: ${unique(item.evidence_ids).length}`} />
          <FactTile label="Tryb" value={data.preflight.preflight_verdict.recommended_mode} />
          <FactTile label="Adres" value="canonical publiczny" />
        </div>
      </div>
    </section>
  );
}

function WorkflowStepsList({ steps }: { steps: WorkflowStep[] }) {
  return (
    <ol aria-label="Kroki workflow treści" className="grid gap-3 lg:grid-cols-3">
      {steps.map((step) => (
        <li key={step.title} className="rounded-md border border-line bg-white p-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 rounded-md border border-line bg-surface p-2 text-action">
              <CheckCircle2 aria-hidden="true" size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-ink">{step.title}</h2>
              <div className="mt-1 text-xs font-medium uppercase tracking-normal text-slate-500">
                {step.status}
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600">{step.summary}</p>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

function WorkflowSafetyPanels({
  data,
  draft,
  handoff,
  window
}: WorkflowSafetyPanelsProps) {
  return (
    <div className="mt-6 grid gap-4 lg:grid-cols-3">
      <SafetyPanel
        icon={<FileText aria-hidden="true" size={18} />}
        title="Paczka szkicu"
        text={draftSafetyText(draft?.publish_ready)}
      />
      <SafetyPanel
        icon={<ShieldCheck aria-hidden="true" size={18} />}
        title="WordPress zostaje w trybie szkicu"
        text={handoffSafetyText(handoff?.publish_allowed)}
      />
      <SafetyPanel
        icon={<Clock3 aria-hidden="true" size={18} />}
        title={data.measurementWindow.outcome_blockers[0]?.label ?? "Nie wolno jeszcze oceniać efektu"}
        text={measurementSafetyText(window)}
      />
    </div>
  );
}

function FactTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 font-semibold text-ink">{value}</div>
    </div>
  );
}

function SafetyPanel({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-md border border-line bg-surface p-2 text-action">{icon}</div>
        <div>
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
        </div>
      </div>
    </section>
  );
}

function draftSafetyText(publishReady?: boolean) {
  if (publishReady) return "Szkic wymaga zatrzymania, bo został oznaczony jako gotowy do publikacji.";
  return "Szkic jest paczką do review, nie tekstem do automatycznej publikacji.";
}

function handoffSafetyText(publishAllowed?: boolean) {
  if (publishAllowed) {
    return "Publikacja wymaga osobnej blokady, bo WILQ nie powinien publikować automatycznie.";
  }
  return "Handoff przygotowuje tylko szkic. Publikacja i nadpisanie treści są zablokowane.";
}

function measurementSafetyText(
  window: ContentWorkflowSnapshot["measurementWindow"]["measurement_window_result"]["window"]
) {
  if (!window) return "Brak okna pomiaru blokuje jakiekolwiek wnioski o efekcie treści.";
  return `Pierwsza ocena po ${window.earliest_verdict_date}. Do tego czasu WILQ zbiera dane, ale nie claimuje sukcesu ani porażki.`;
}

function unique(values: string[]) {
  return Array.from(new Set(values));
}
