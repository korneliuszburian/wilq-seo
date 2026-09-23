import { Fragment } from "react";

import { ACTION_LIFECYCLE_ORDER } from "./lifecycleOrder";
import { ActionPreviewControls } from "./PreviewControls";
import { ActionHumanReviewControls } from "./ReviewControls";
import type { ActionPanelProps } from "./shared";
import {
  ActionConfirmationApplyControls,
  ActionValidationOnlyControls
} from "./ValidationApplyControls";

export function ActionLifecycleControls({ action }: ActionPanelProps) {
  return (
    <>
      {ACTION_LIFECYCLE_ORDER.map((step) => (
        <Fragment key={step}>
          {step === "validate" ? <ActionValidationOnlyControls action={action} /> : null}
          {step === "preview" ? <ActionPreviewControls action={action} /> : null}
          {step === "review" ? <ActionHumanReviewControls action={action} /> : null}
          {step === "confirm_impact_apply" ? <ActionConfirmationApplyControls action={action} /> : null}
        </Fragment>
      ))}
    </>
  );
}
