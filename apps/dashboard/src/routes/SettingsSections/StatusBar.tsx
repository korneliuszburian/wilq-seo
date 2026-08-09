import { ChevronDown, ChevronRight, ShieldCheck } from "lucide-react";

export function SourceStatTile({
  value,
  label,
  tone
}: {
  value: number;
  label: string;
  tone: "default" | "success" | "risk" | "wait";
}) {
  const toneClass =
    tone === "success"
      ? "bg-success/10 text-success"
      : tone === "risk"
        ? "bg-risk/10 text-risk"
        : tone === "wait"
          ? "bg-wait/10 text-wait"
          : "bg-action/10 text-action";
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex items-center gap-4">
        <div className={`flex h-11 w-11 items-center justify-center rounded-full ${toneClass}`}>
          <ShieldCheck size={20} aria-hidden="true" />
        </div>
        <div>
          <div className="text-2xl font-semibold text-ink">{value}</div>
          <div className="text-sm text-slate-700">{label}</div>
        </div>
      </div>
    </article>
  );
}

export function SectionHeading({ title }: { title: string }) {
  return <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-slate-600">{title}</h2>;
}

export function DetailToggle({
  expanded,
  label,
  onClick
}: {
  expanded: boolean;
  label: string;
  onClick: () => void;
}) {
  const Icon = expanded ? ChevronDown : ChevronRight;
  return (
    <button
      type="button"
      aria-expanded={expanded}
      onClick={onClick}
      className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
    >
      <Icon aria-hidden="true" size={16} />
      {label}
    </button>
  );
}
