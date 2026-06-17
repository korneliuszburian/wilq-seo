type StatusBadgeProps = {
  value: string;
};

const palette: Record<string, string> = {
  configured: "border-signal/30 bg-signal/10 text-signal",
  missing_credentials: "border-wait/30 bg-wait/10 text-wait",
  blocked: "border-risk/30 bg-risk/10 text-risk",
  ready_to_apply: "border-action/30 bg-action/10 text-action"
};

export function StatusBadge({ value }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex min-h-7 items-center rounded border px-2 text-xs font-medium ${
        palette[value] ?? "border-line bg-white text-ink"
      }`}
    >
      {value.replaceAll("_", " ")}
    </span>
  );
}

