import type { getActionMutationReadiness } from "../../lib/api";

export type ActionMutationReadiness = Awaited<
  ReturnType<typeof getActionMutationReadiness>
>;

export function SectionHeading({ title }: { title: string }) {
  return <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-slate-600">{title}</h2>;
}
