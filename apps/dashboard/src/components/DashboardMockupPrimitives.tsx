import type { ReactNode } from "react";
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleSlash,
  Clock3,
  ListChecks,
  RefreshCw
} from "lucide-react";

type Tone = "neutral" | "blue" | "green" | "amber" | "red" | "purple";
type Risk = "low" | "medium" | "high" | "blocked" | "unknown";
type Priority = "P1" | "P2" | "P3" | "-";

type DashboardToolbarProps = {
  title: string;
  description?: string;
  dateLabel: string;
  refreshLabel?: string;
  onRefresh?: () => void;
  dateControlLabel?: string;
};

export function DashboardToolbar({
  title,
  description,
  dateLabel,
  refreshLabel = "Odśwież",
  onRefresh,
  dateControlLabel = "Zakres daty"
}: DashboardToolbarProps) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-3xl font-semibold tracking-normal text-ink">{title}</h1>
        {description ? (
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          aria-label={dateControlLabel}
          className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-slate-700 shadow-sm"
        >
          <CalendarDays aria-hidden="true" size={16} className="text-action" />
          {dateLabel}
          <ChevronDown aria-hidden="true" size={16} className="text-slate-500" />
        </button>
        <button
          type="button"
          onClick={onRefresh}
          className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-slate-700 shadow-sm"
        >
          <RefreshCw aria-hidden="true" size={16} />
          {refreshLabel}
        </button>
      </div>
    </div>
  );
}

type StatTileProps = {
  value: number | string;
  label: string;
  actionLabel?: string;
  tone?: Tone;
  icon?: ReactNode;
};

export function CompactStatTile({
  value,
  label,
  actionLabel,
  tone = "blue",
  icon
}: StatTileProps) {
  return (
    <article className="min-h-28 rounded-md border border-line bg-white p-4 shadow-sm">
      <div className="flex items-center gap-4">
        <div
          className={joinClasses(
            "flex size-12 shrink-0 items-center justify-center rounded-full",
            statToneClasses[tone]
          )}
        >
          {icon ?? <ListChecks aria-hidden="true" size={22} />}
        </div>
        <div className="min-w-0">
          <div className="text-3xl font-semibold leading-none text-ink">
            {formatTileValue(value)}
          </div>
          <div className="mt-1 text-sm leading-5 text-slate-700">{label}</div>
        </div>
      </div>
      {actionLabel ? (
        <div className={joinClasses("mt-3 text-sm font-medium", actionToneClasses[tone])}>
          {actionLabel}
        </div>
      ) : null}
    </article>
  );
}

type SourceFreshnessItem = {
  label: string;
  detail: string;
  tone?: Tone;
  icon?: ReactNode;
};

export function SourceFreshnessStrip({ items }: { items: SourceFreshnessItem[] }) {
  if (items.length === 0) return null;

  return (
    <section
      aria-label="Świeżość źródeł"
      className="grid gap-0 overflow-hidden rounded-md border border-line bg-white shadow-sm sm:grid-cols-2 lg:grid-cols-4"
    >
      {items.map((item, index) => (
        <div
          key={`${item.label}:${item.detail}`}
          className={joinClasses(
            "flex min-h-12 items-center gap-3 px-4 py-3 text-sm",
            index > 0 ? "border-t border-line sm:border-t-0 sm:border-l" : ""
          )}
        >
          <span className={joinClasses("text-slate-500", actionToneClasses[item.tone ?? "neutral"])}>
            {item.icon ?? <Clock3 aria-hidden="true" size={16} />}
          </span>
          <span className="font-semibold text-ink">{item.label}</span>
          <span className={joinClasses("ml-auto", actionToneClasses[item.tone ?? "neutral"])}>
            {item.detail}
          </span>
        </div>
      ))}
    </section>
  );
}

type BlockerPanelProps = {
  title: string;
  badgeLabel?: string;
  items: Array<{
    title: string;
    description?: string;
    tone?: Tone;
    href?: string;
  }>;
  footer?: ReactNode;
};

export function BlockerPanel({ title, badgeLabel, items, footer }: BlockerPanelProps) {
  return (
    <section className="overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="flex min-h-12 items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold text-ink">{title}</h2>
        {badgeLabel ? <StatusPill label={badgeLabel} tone="red" /> : null}
      </div>
      <div className="divide-y divide-line">
        {items.map((item) => {
          const content = (
            <>
              <AlertTriangle
                aria-hidden="true"
                size={16}
                className={joinClasses("mt-0.5 shrink-0", actionToneClasses[item.tone ?? "red"])}
              />
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-ink">{item.title}</span>
                {item.description ? (
                  <span className="mt-0.5 block text-sm leading-5 text-slate-600">
                    {item.description}
                  </span>
                ) : null}
              </span>
              {item.href ? (
                <ChevronRight aria-hidden="true" size={16} className="ml-auto shrink-0 text-slate-500" />
              ) : null}
            </>
          );

          return item.href ? (
            <a
              key={`${item.title}:${item.href}`}
              href={item.href}
              className="flex items-start gap-3 px-4 py-3 hover:bg-slate-50"
            >
              {content}
            </a>
          ) : (
            <div key={item.title} className="flex items-start gap-3 px-4 py-3">
              {content}
            </div>
          );
        })}
      </div>
      {footer ? <div className="border-t border-line px-4 py-3">{footer}</div> : null}
    </section>
  );
}

export function ForbiddenClaimsStrip({ claims }: { claims: string[] }) {
  if (claims.length === 0) return null;

  return (
    <section className="rounded-md border border-line bg-white px-4 py-3 shadow-sm">
      <h2 className="mb-3 text-base font-semibold text-ink">Nie wolno dziś twierdzić</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {claims.map((claim) => (
          <div key={claim} className="flex items-center gap-2 text-sm text-slate-700">
            <CircleSlash aria-hidden="true" size={16} className="shrink-0 text-amber-600" />
            <span>{claim}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

type DashboardTableColumn<TRow> = {
  key: string;
  header: string;
  render: (row: TRow) => ReactNode;
  className?: string;
};

type DashboardTableProps<TRow> = {
  title: string;
  columns: Array<DashboardTableColumn<TRow>>;
  rows: TRow[];
  getRowKey: (row: TRow, index: number) => string;
  action?: ReactNode;
  selectedRowKey?: string;
  emptyLabel?: string;
};

export function DenseQueueTable<TRow>({
  title,
  columns,
  rows,
  getRowKey,
  action,
  selectedRowKey,
  emptyLabel = "Brak pozycji do pokazania"
}: DashboardTableProps<TRow>) {
  return (
    <section className="overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="flex min-h-14 items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold text-ink">{title}</h2>
        {action}
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold text-slate-700">
            <tr>
              {columns.map((column) => (
                <th key={column.key} scope="col" className={joinClasses("px-4 py-3", column.className)}>
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-5 text-sm text-slate-600">
                  {emptyLabel}
                </td>
              </tr>
            ) : (
              rows.map((row, index) => {
                const rowKey = getRowKey(row, index);
                const selected = rowKey === selectedRowKey;
                return (
                  <tr
                    key={rowKey}
                    className={joinClasses(
                      "align-middle text-slate-700",
                      selected ? "bg-blue-50 ring-1 ring-inset ring-action" : "bg-white"
                    )}
                  >
                    {columns.map((column) => (
                      <td key={`${rowKey}:${column.key}`} className={joinClasses("px-4 py-3", column.className)}>
                        {column.render(row)}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function PriorityBadge({ value }: { value: Priority }) {
  return (
    <span
      className={joinClasses(
        "inline-flex min-w-10 justify-center rounded border px-2 py-1 text-xs font-semibold",
        priorityClasses[value]
      )}
    >
      {value}
    </span>
  );
}

export function StatusPill({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  return (
    <span
      className={joinClasses(
        "inline-flex min-h-7 items-center rounded-md border px-2.5 text-xs font-semibold",
        pillToneClasses[tone]
      )}
    >
      {label}
    </span>
  );
}

export function RiskPill({ label, risk = "unknown" }: { label: string; risk?: Risk }) {
  return (
    <span
      className={joinClasses(
        "inline-flex min-h-7 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium",
        riskClasses[risk]
      )}
    >
      <span className={joinClasses("size-2 rounded-full", riskDotClasses[risk])} />
      {label}
    </span>
  );
}

type LifecycleStep = {
  label: string;
  state: "done" | "current" | "blocked" | "waiting";
};

export function ActionLifecycleStrip({ steps }: { steps: LifecycleStep[] }) {
  if (steps.length === 0) return null;

  return (
    <section
      aria-label="Cykl bezpiecznej akcji"
      className="rounded-md border border-line bg-white px-4 py-3 shadow-sm"
    >
      <div className="grid gap-2 md:grid-cols-5">
        {steps.map((step, index) => (
          <div key={`${step.label}:${index}`} className="flex items-center gap-2 text-sm">
            <span
              className={joinClasses(
                "flex size-7 shrink-0 items-center justify-center rounded-full border",
                lifecycleClasses[step.state]
              )}
            >
              {step.state === "done" ? <CheckCircle2 aria-hidden="true" size={15} /> : index + 1}
            </span>
            <span className="font-medium text-slate-700">{step.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function formatTileValue(value: number | string) {
  if (typeof value !== "number") return value;
  return new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(value);
}

function joinClasses(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

const statToneClasses: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-700",
  blue: "bg-blue-100 text-action",
  green: "bg-emerald-100 text-signal",
  amber: "bg-amber-100 text-amber-700",
  red: "bg-red-100 text-risk",
  purple: "bg-violet-100 text-violet-700"
};

const actionToneClasses: Record<Tone, string> = {
  neutral: "text-slate-600",
  blue: "text-action",
  green: "text-signal",
  amber: "text-amber-700",
  red: "text-risk",
  purple: "text-violet-700"
};

const pillToneClasses: Record<Tone, string> = {
  neutral: "border-line bg-slate-50 text-slate-700",
  blue: "border-blue-200 bg-blue-50 text-action",
  green: "border-emerald-200 bg-emerald-50 text-signal",
  amber: "border-amber-200 bg-amber-50 text-amber-700",
  red: "border-red-200 bg-red-50 text-risk",
  purple: "border-violet-200 bg-violet-50 text-violet-700"
};

const priorityClasses: Record<Priority, string> = {
  P1: "border-red-300 bg-red-50 text-risk",
  P2: "border-amber-300 bg-amber-50 text-amber-700",
  P3: "border-slate-300 bg-slate-50 text-slate-700",
  "-": "border-slate-200 bg-slate-50 text-slate-500"
};

const riskClasses: Record<Risk, string> = {
  low: "border-emerald-200 bg-white text-slate-700",
  medium: "border-amber-200 bg-white text-slate-700",
  high: "border-red-200 bg-white text-slate-700",
  blocked: "border-red-200 bg-red-50 text-risk",
  unknown: "border-slate-200 bg-white text-slate-600"
};

const riskDotClasses: Record<Risk, string> = {
  low: "bg-signal",
  medium: "bg-amber-500",
  high: "bg-risk",
  blocked: "bg-risk",
  unknown: "bg-slate-400"
};

const lifecycleClasses: Record<LifecycleStep["state"], string> = {
  done: "border-emerald-200 bg-emerald-50 text-signal",
  current: "border-blue-200 bg-blue-50 text-action",
  blocked: "border-red-200 bg-red-50 text-risk",
  waiting: "border-slate-200 bg-slate-50 text-slate-500"
};
