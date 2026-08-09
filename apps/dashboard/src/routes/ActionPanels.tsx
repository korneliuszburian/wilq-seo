import { Link } from "@tanstack/react-router";

import { ActionTechnicalDataToggle } from "../components/ActionTechnicalDataToggle";
import { MetricFactChips } from "../components/MetricFactChips";
import { BlockerNotice } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import { ActionReviewGatePanel } from "./ActionPanels/GatePanel";
import { ActionPreviewControls } from "./ActionPanels/PreviewControls";
import { ActionHumanReviewControls } from "./ActionPanels/ReviewControls";
import type { ActionObject, PayloadRecord } from "./ActionPanels/shared";
import {
  ActionNewPageDraftApplyControl,
  ActionValidationControls
} from "./ActionPanels/ValidationApplyControls";

export {
  ActionHumanReviewControls,
  ActionNewPageDraftApplyControl,
  ActionPreviewControls,
  ActionReviewGatePanel,
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
            <ActionPayloadSummary action={action} />
            <ActionHumanReviewControls action={action} />
            <ActionPreviewControls action={action} />
            <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
              <TraceLine label="Akcja" values={["1 akcja do sprawdzenia"]} />
              <ActionEvidenceTrace action={action} />
            </div>
            {action.metrics.length > 0 ? <MetricFactChips facts={action.metrics.slice(0, 5)} /> : null}
            <ActionValidationControls action={action} />
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

function asRecord(value: unknown): PayloadRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as PayloadRecord;
}

function recordsValue(record: PayloadRecord, key: string): PayloadRecord[] {
  const value = record[key];
  if (!Array.isArray(value)) return [];
  return value.map(asRecord).filter((item): item is PayloadRecord => Boolean(item));
}

function stringValue(record: PayloadRecord | null, key: string): string {
  const value = record?.[key];
  return typeof value === "string" ? value.trim() : "";
}

function stringListValue(record: PayloadRecord | null, key: string): string[] {
  const value = record?.[key];
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function numberValue(record: PayloadRecord | null, key: string): number | null {
  const value = record?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function ActionPayloadSummary({ action }: { action: ActionObject }) {
  const payload = asRecord(action.payload);
  if (!payload) return null;

  const campaignCandidates = recordsValue(payload, "campaign_candidates");
  if (campaignCandidates.length > 0) {
    return <CampaignPayloadSummary candidates={campaignCandidates} />;
  }

  const recommendations = recordsValue(payload, "recommendations");
  if (recommendations.length > 0) {
    return <RecommendationPayloadSummary recommendations={recommendations} />;
  }

  return null;
}

function CampaignPayloadSummary({ candidates }: { candidates: PayloadRecord[] }) {
  const first = candidates[0] ?? null;
  const campaignName = stringValue(first, "campaign_name") || "kampania do sprawdzenia";
  const reviewPriority = stringValue(first, "review_priority");
  const reviewReason = stringValue(first, "review_reason");
  const reviewScore = numberValue(first, "review_score");
  const validationLabels = stringListValue(first, "human_review_gate_labels");
  const blockedClaimLabels = stringListValue(first, "blocked_claim_labels");

  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-xs leading-5 text-slate-700">
      <div className="font-semibold uppercase tracking-normal text-slate-600">
        Co obejmuje akcja
      </div>
      <p className="mt-1">
        {candidates.length === 1
          ? `WILQ przygotował 1 kampanię do review: ${campaignName}.`
          : `WILQ przygotował ${candidates.length} kampanii do review; pierwsza w kolejce: ${campaignName}.`}
        {reviewPriority ? ` Priorytet: ${reviewPriority}.` : ""}
        {reviewScore !== null ? ` Wynik review: ${reviewScore}/100.` : ""}
      </p>
      {reviewReason ? <p className="mt-1 text-slate-600">{reviewReason}</p> : null}
      <div className="mt-2 grid gap-1">
        <TraceLine
          label="Wymagane sprawdzenia"
          values={validationLabels.slice(0, 5)}
          empty="WILQ nie podał listy sprawdzeń dla kampanii."
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={blockedClaimLabels.slice(0, 5)}
          empty="WILQ nie podał osobnych blokad twierdzeń dla kampanii."
        />
      </div>
    </div>
  );
}

function RecommendationPayloadSummary({ recommendations }: { recommendations: PayloadRecord[] }) {
  const first = recommendations[0] ?? null;
  const preview = asRecord(first?.payload_preview);
  const recommendationLabel =
    stringValue(first, "recommendation_type_label") || "rekomendacja do sprawdzenia";
  const previewReason = stringValue(preview, "reason");
  const validationLabels = stringListValue(first, "required_validation_labels");
  const blockedClaimLabels = stringListValue(first, "blocked_claim_labels");

  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-xs leading-5 text-slate-700">
      <div className="font-semibold uppercase tracking-normal text-slate-600">
        Co obejmuje akcja
      </div>
      <p className="mt-1">
        {recommendations.length === 1
          ? `WILQ przygotował 1 rekomendację Google Ads do review: ${recommendationLabel}.`
          : `WILQ przygotował ${recommendations.length} rekomendacji Google Ads do review; pierwsza: ${recommendationLabel}.`}
      </p>
      {previewReason ? <p className="mt-1 text-slate-600">{previewReason}</p> : null}
      <div className="mt-2 grid gap-1">
        <TraceLine
          label="Wymagane sprawdzenia"
          values={validationLabels.slice(0, 5)}
          empty="WILQ nie podał listy sprawdzeń rekomendacji."
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={blockedClaimLabels.slice(0, 5)}
          empty="WILQ nie podał osobnych blokad twierdzeń rekomendacji."
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
