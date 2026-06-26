import { AlertTriangle, RefreshCw } from "lucide-react";

export function LoadingBand() {
  return (
    <div className="flex h-32 items-center gap-3 px-6 text-sm text-slate-600">
      <RefreshCw aria-hidden="true" className="animate-spin" size={18} />
      Ładowanie stanu WILQ
    </div>
  );
}

export function BlockerNotice({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-wait/30 bg-wait/10 p-4 text-sm leading-6 text-wait">
      <AlertTriangle aria-hidden="true" className="mt-0.5 shrink-0" size={16} />
      <span>{message}</span>
    </div>
  );
}

export function MetricTile({
  label,
  value
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div className="min-w-24 rounded-md border border-line bg-white px-3 py-2">
      <div className="text-lg font-semibold">{value}</div>
      <div className="text-slate-500">{label}</div>
    </div>
  );
}
