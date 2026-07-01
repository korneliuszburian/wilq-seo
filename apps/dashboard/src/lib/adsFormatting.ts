export function adsStrategyContextValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "wartość do potwierdzenia";
  if (typeof value === "number") return adsNumber(value);
  return String(value);
}

export function adsNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "wartość do potwierdzenia";
  return new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 4 }).format(value);
}

export function adsCost(value: number | null | undefined, currencyCode?: string) {
  if (value === null || value === undefined) return "koszt do potwierdzenia";
  const accountUnits = value / 1_000_000;
  if (currencyCode) {
    return new Intl.NumberFormat("pl-PL", {
      currency: currencyCode,
      maximumFractionDigits: 2,
      style: "currency"
    }).format(accountUnits);
  }
  return `${new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(
    accountUnits
  )} jedn. konta`;
}

export function adsSignedCost(value: number | null | undefined, currencyCode?: string) {
  if (value === null || value === undefined) return "zmiana kosztu do potwierdzenia";
  const formatted = adsCost(Math.abs(value), currencyCode);
  if (value > 0) return `+${formatted}`;
  if (value < 0) return `-${formatted}`;
  return formatted;
}

export function adsSignedNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "zmiana do potwierdzenia";
  if (value > 0) return `+${adsNumber(value)}`;
  return adsNumber(value);
}

export function adsTargetStatusClass(status: string | null | undefined) {
  const base = "inline-flex whitespace-nowrap rounded border px-2 py-1 font-semibold";
  if (status === "spend_without_conversions") {
    return `${base} border-amber-200 bg-amber-50 text-amber-800`;
  }
  if (status === "outside_target") {
    return `${base} border-rose-200 bg-rose-50 text-rose-800`;
  }
  if (status === "within_target") {
    return `${base} border-emerald-200 bg-emerald-50 text-emerald-800`;
  }
  return `${base} border-slate-200 bg-slate-50 text-slate-600`;
}

export function adsPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "udział do potwierdzenia";
  return `${new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(
    value * 100
  )}%`;
}
