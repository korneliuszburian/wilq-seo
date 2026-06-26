type StatusBadgeProps = {
  value: string;
};

const palette: Record<string, string> = {
  configured: "border-signal/30 bg-signal/10 text-signal",
  ready: "border-signal/30 bg-signal/10 text-signal",
  review_ready: "border-signal/30 bg-signal/10 text-signal",
  completed: "border-signal/30 bg-signal/10 text-signal",
  missing_credentials: "border-wait/30 bg-wait/10 text-wait",
  needs_validation: "border-wait/30 bg-wait/10 text-wait",
  not_validated: "border-wait/30 bg-wait/10 text-wait",
  stale: "border-wait/30 bg-wait/10 text-wait",
  unknown: "border-wait/30 bg-wait/10 text-wait",
  missing: "border-wait/30 bg-wait/10 text-wait",
  blocked: "border-risk/30 bg-risk/10 text-risk",
  failed: "border-risk/30 bg-risk/10 text-risk",
  disabled: "border-slate-300 bg-slate-100 text-slate-600",
  ready_to_apply: "border-action/30 bg-action/10 text-action"
};

const labels: Record<string, string> = {
  configured: "aktywne",
  ready: "gotowe",
  review_ready: "gotowe do sprawdzenia",
  completed: "zakończone",
  missing_credentials: "brak dostępu",
  needs_validation: "do sprawdzenia",
  not_validated: "niesprawdzone",
  stale: "do odświeżenia",
  unknown: "świeżość nieznana",
  missing: "brak danych",
  blocked: "zablokowane",
  failed: "błąd",
  disabled: "wyłączone",
  ready_to_apply: "gotowe do potwierdzenia",
  low: "niskie ryzyko",
  medium: "średnie ryzyko",
  high: "wysokie ryzyko",
  critical: "krytyczne"
};

export function StatusBadge({ value }: StatusBadgeProps) {
  const label = labels[value] ?? value;

  return (
    <span
      className={`inline-flex min-h-7 items-center rounded border px-2 text-xs font-medium ${
        palette[value] ?? "border-line bg-white text-ink"
      }`}
    >
      {label}
    </span>
  );
}
