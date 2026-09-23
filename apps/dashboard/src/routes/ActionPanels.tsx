import { Link } from "@tanstack/react-router";

import { ActionPreviewCard } from "../components/ActionPreviewCard";
import { ActionTechnicalDataToggle } from "../components/ActionTechnicalDataToggle";
import { MetricFactChips } from "../components/MetricFactChips";
import { BlockerNotice } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import { ActionReviewGatePanel } from "./ActionPanels/GatePanel";
import { ActionLifecycleControls } from "./ActionPanels/LifecycleControls";
import { ActionPreviewControls } from "./ActionPanels/PreviewControls";
import { ActionHumanReviewControls } from "./ActionPanels/ReviewControls";
import type { ActionObject } from "./ActionPanels/shared";
import {
  ActionConfirmationApplyControls,
  ActionNewPageDraftApplyControl,
  ActionValidationOnlyControls,
  ActionValidationControls
} from "./ActionPanels/ValidationApplyControls";

export {
  ActionHumanReviewControls,
  ActionNewPageDraftApplyControl,
  ActionPreviewControls,
  ActionReviewGatePanel,
  ActionLifecycleControls,
  ActionValidationOnlyControls,
  ActionConfirmationApplyControls,
  ActionValidationControls
};

export function ActionFocus({ actions }: { actions: ActionObject[] }) {
  if (actions.length === 0) {
    return (
      <BlockerNotice message="Brak akcji dla tego procesu. WILQ może pokazać dowody, ale nie powinien sugerować zapisu zmian bez podglądu." />
    );
  }

  return (
    <section>
      <SectionHeading title="Akcje do sprawdzenia" />
      <div className="grid gap-3 xl:grid-cols-2">
        {actions.map((action) => (
          <article key={action.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">{action.title}</h3>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
                  <span>Źródła danych: {action.connector_label}</span>
                  <span>Tryb pracy: {action.mode_label}</span>
                </div>
              </div>
              <StatusBadge
                value={action.validation_status}
                label={action.validation_status_label}
              />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{action.human_diagnosis}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge value={action.status} label={action.status_label} />
              <StatusBadge value={action.risk} label={action.risk_label} />
            </div>
            {action.mode !== "apply" ? (
              <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-xs leading-5 text-wait">
                Zapis zmian zablokowany: ta akcja jest w trybie przygotowania.
                Najpierw sprawdzenie w WILQ, podgląd zmian i jawna zgoda operatora.
              </div>
            ) : null}
            <ActionDecisionSummary action={action} />
            <ActionReviewGatePanel action={action} />
            {action.preview_cards.length > 0 ? (
              <div className="mt-3 grid gap-2">
                {action.preview_cards.map((card) => (
                  <ActionPreviewCard key={card.id} card={card} />
                ))}
              </div>
            ) : null}
            <ActionLifecycleControls action={action} />
            <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
              <TraceLine label="Akcja" values={["1 akcja do sprawdzenia"]} />
              <ActionEvidenceTrace action={action} />
            </div>
            {action.metrics.length > 0 ? <MetricFactChips facts={action.metrics.slice(0, 5)} /> : null}
            <ActionTechnicalDataToggle
              technicalData={action.payload}
              intro="Domyślnie schowany, żeby karta pokazywała decyzję i warunki przeglądu."
            />
          </article>
        ))}
      </div>
    </section>
  );
}

function ActionEvidenceTrace({ action }: { action: ActionObject }) {
  const summaryLabel = action.evidence_summary_label.trim();

  if (!summaryLabel) {
    return (
      <TraceLine
        label="Dowody"
        values={[]}
        empty="WILQ nie podał podsumowania dowodów; nie traktuj tej akcji jako gotowej rekomendacji."
      />
    );
  }

  return (
    <div className="break-words">
      Dowody: <span>{summaryLabel}</span>
      {action.evidence_ids.length > 0 ? (
        <span>
          {" "}
          (
          {action.evidence_ids.map((evidenceId, index) => (
            <span key={evidenceId}>
              {index > 0 ? ", " : ""}
              <Link
                to="/evidence/$evidenceId"
                params={{ evidenceId }}
                className="font-medium text-action underline-offset-2 hover:underline"
              >
                dowód {index + 1}
              </Link>
            </span>
          ))}
          )
        </span>
      ) : null}
    </div>
  );
}

function ActionDecisionSummary({ action }: { action: ActionObject }) {
  const firstChecks = action.review_gate.operator_checklist_labels.slice(0, 3);
  const writeBlockerSummary = action.review_gate.apply_blocker_summary_label.trim();
  const reason = action.recommended_reason.trim();

  return (
    <div className="mt-3 rounded-md border border-action/20 bg-action/5 p-3 text-xs leading-5 text-slate-700">
      <div className="font-semibold uppercase tracking-normal text-slate-600">
        Co sprawdzić przed decyzją
      </div>
      <p className="mt-1">
        {reason || "WILQ przygotował akcję do ręcznego przeglądu na podstawie dowodów."}
      </p>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        <TraceLine
          label="Najpierw sprawdź"
          values={firstChecks}
          empty="WILQ nie podał szczegółowej checklisty; zacznij od dowodów, podglądu i decyzji człowieka."
        />
        <TraceLine
          label="Przed zapisem blokuje"
          values={writeBlockerSummary ? [writeBlockerSummary] : []}
          empty="WILQ nie podał blokad zapisu; nadal wymagaj podglądu i jawnej zgody."
        />
      </div>
    </div>
  );
}

export function ActionIdFocus({
  actionIds,
  actionSummaryLabel,
  note
}: {
  actionIds: string[];
  actionSummaryLabel: string;
  note: string;
}) {
  return (
    <section>
      <SectionHeading title="Akcje do sprawdzenia" />
      <div className="rounded-md border border-line bg-white p-4 text-sm leading-6 text-slate-700">
        <p>{note}</p>
        <div className="mt-3">
          <TraceLine
            label="Akcje"
            values={actionIds.length > 0 ? [actionSummaryLabel] : []}
            empty="WILQ nie podał akcji do sprawdzenia; pokazuj tylko notatkę procesu."
          />
        </div>
      </div>
    </section>
  );
}

function SectionHeading({ title }: { title: string }) {
  return (
    <h2 className="mb-3 text-xs font-semibold uppercase tracking-normal text-slate-500">
      {title}
    </h2>
  );
}
