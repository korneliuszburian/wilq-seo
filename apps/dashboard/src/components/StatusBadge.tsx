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
  blocked: "border-risk/30 bg-risk/10 text-risk",
  failed: "border-risk/30 bg-risk/10 text-risk",
  ready_to_apply: "border-action/30 bg-action/10 text-action"
};

const labels: Record<string, string> = {
  configured: "aktywne",
  ready: "gotowe",
  review_ready: "gotowe do review",
  completed: "zakończone",
  missing_credentials: "brak dostępu",
  needs_validation: "do walidacji",
  not_validated: "niezwalidowane",
  blocked: "zablokowane",
  failed: "błąd",
  ready_to_apply: "gotowe do potwierdzenia",
  low: "niskie ryzyko",
  medium: "średnie ryzyko",
  high: "wysokie ryzyko",
  critical: "krytyczne"
};

export function StatusBadge({ value }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex min-h-7 items-center rounded border px-2 text-xs font-medium ${
        palette[value] ?? "border-line bg-white text-ink"
      }`}
    >
      {labels[value] ?? value.replaceAll("_", " ")}
    </span>
  );
}
