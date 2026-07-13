import { Stamp } from "lucide-react";

import { ContentWorkflowControlButton as WorkflowControlButton } from "./ContentWorkflowControlButton";

export type WorkflowControlItem = {
  label: string;
  disabledReason: string | null;
  pending: boolean;
  onClick: () => void;
};

export function WorkflowOperatorControls({
  controls,
  topic
}: {
  controls: WorkflowControlItem[];
  topic: string;
}) {
  return (
    <section id="content-workflow-actions" className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Stamp aria-hidden="true" size={18} className="text-action" />
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Decyzje operatora</h2>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Te przyciski zapisują sprawdzenie i audyt w WILQ. Nie publikują treści, nie nadpisują strony i nie tworzą publicznego wpisu w WordPress.
          </p>
          <p className="mt-2 text-xs text-slate-500">Temat: <span className="font-medium text-ink">{topic}</span></p>
        </div>
        <div className="grid w-full gap-3 sm:w-auto sm:min-w-80">
          {controls.map((control) => <WorkflowControlButton key={control.label} {...control} />)}
        </div>
      </div>
    </section>
  );
}
