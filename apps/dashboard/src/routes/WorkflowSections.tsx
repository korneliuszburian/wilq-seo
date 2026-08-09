import { type Workflow, type WorkflowRun } from "../lib/api";
import { SectionHeading } from "./SettingsSections";
import { WorkflowRunList } from "./WorkflowPanels";

export function WorkflowSurfaceSections({
  workflows,
  workflowRuns
}: {
  workflows: Workflow[];
  workflowRuns: WorkflowRun[];
}) {
  return (
    <>
      <section>
        <SectionHeading title="Procesy decyzyjne" />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {workflows.map((workflow) => (
            <article key={workflow.id} className="rounded-md border border-line bg-white p-4">
              <h3 className="text-sm font-semibold">{workflow.label}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-700">{workflow.description}</p>
            </article>
          ))}
        </div>
      </section>
      <section>
        <SectionHeading title="Ostatnie uruchomienia" />
        <WorkflowRunList runs={workflowRuns} />
      </section>
    </>
  );
}
