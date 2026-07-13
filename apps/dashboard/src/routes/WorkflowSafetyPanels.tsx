import { Clock3, FileText, ShieldCheck } from "lucide-react";

import { ContentQualityReviewPanel } from "./ContentQualityReviewPanel";
import { ContentRevisionPlanPanel } from "./ContentRevisionPlanPanel";
import { AcfPreviewPanel } from "./AcfPreviewPanel";
import { StructuredDraftPreviewPanel } from "./StructuredDraftPreviewPanel";
import { ContentSafetyPanel as SafetyPanel } from "./ContentSafetyPanel";

export type WorkflowSafetyPanelsProps = {
  draftSafetyText: string;
  structuredRuntimeSafetyText: string;
  structuredPreviewSafetyText: string;
  qualityReviewSafetyText: string;
  revisionPlanSafetyText: string;
  acfPreviewSafetyText: string;
  handoffSafetyText: string;
  executionSafetyText: string;
  measurementTitle: string;
  measurementSafetyText: string;
  structuredPreviewResult: Parameters<typeof StructuredDraftPreviewPanel>[0]["result"];
  qualityReview: Parameters<typeof ContentQualityReviewPanel>[0]["review"];
  revisionPlan: Parameters<typeof ContentRevisionPlanPanel>[0]["plan"];
  acfPreviewResult: Parameters<typeof AcfPreviewPanel>[0]["result"];
};

export function WorkflowSafetyPanels({
  draftSafetyText,
  structuredRuntimeSafetyText,
  structuredPreviewSafetyText,
  qualityReviewSafetyText,
  revisionPlanSafetyText,
  acfPreviewSafetyText,
  handoffSafetyText,
  executionSafetyText,
  measurementTitle,
  measurementSafetyText,
  structuredPreviewResult,
  qualityReview,
  revisionPlan,
  acfPreviewResult
}: WorkflowSafetyPanelsProps) {
  return (
    <div className="mt-6 grid gap-4 lg:grid-cols-3">
      <SafetyPanel icon={<FileText aria-hidden="true" size={18} />} title="Paczka szkicu" text={draftSafetyText} />
      <SafetyPanel icon={<ShieldCheck aria-hidden="true" size={18} />} title="Szkic treści" text={structuredRuntimeSafetyText} />
      <StructuredDraftPreviewPanel result={structuredPreviewResult} safetyText={structuredPreviewSafetyText} />
      <ContentQualityReviewPanel review={qualityReview} safetyText={qualityReviewSafetyText} />
      <ContentRevisionPlanPanel plan={revisionPlan} safetyText={revisionPlanSafetyText} />
      <AcfPreviewPanel result={acfPreviewResult} safetyText={acfPreviewSafetyText} />
      <SafetyPanel icon={<ShieldCheck aria-hidden="true" size={18} />} title="WordPress zostaje w trybie szkicu" text={handoffSafetyText} />
      <SafetyPanel icon={<ShieldCheck aria-hidden="true" size={18} />} title="Podgląd szkicu WordPress" text={executionSafetyText} />
      <SafetyPanel icon={<Clock3 aria-hidden="true" size={18} />} title={measurementTitle} text={measurementSafetyText} />
    </div>
  );
}
