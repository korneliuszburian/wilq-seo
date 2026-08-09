import type { ConnectorStatus } from "../../lib/api";

export function sourceAccessStatus(connector: ConnectorStatus) {
  if (hasMissingSourceAccess(connector)) {
    return {
      label: "Brak dostępu",
      className: "bg-risk/10 text-risk",
      description: "Dostęp wymaga uzupełnienia przed decyzjami z tego kanału."
    };
  }
  if (!connector.active_for_daily_work) {
    return {
      label: "Poza zakresem",
      className: "bg-wait/10 text-wait",
      description: "Dane nie są liczone do głównego dziennego zakresu pracy."
    };
  }
  if (hasStaleSourceData(connector)) {
    return {
      label: "Do odświeżenia",
      className: "bg-wait/10 text-wait",
      description: "Dane są dostępne, ale nie powinny domykać decyzji bez świeżego odczytu."
    };
  }
  if (connector.configured) {
    return {
      label: "Aktywny",
      className: "bg-success/10 text-success",
      description: "Dane dostępne i aktualizowane przez WILQ."
    };
  }
  return {
    label: connector.status_label || "Do sprawdzenia",
    className: "bg-wait/10 text-wait",
    description: "Status wymaga sprawdzenia przed użyciem w decyzjach."
  };
}

export function hasMissingSourceAccess(connector: ConnectorStatus) {
  return connector.missing_credentials.length > 0 || connector.status === "missing_credentials";
}

export function hasStaleSourceData(connector: ConnectorStatus) {
  return (
    connector.active_for_daily_work
    && connector.configured
    && !hasMissingSourceAccess(connector)
    && connector.freshness.state === "stale"
  );
}

export type SourceImpactRow = {
  id: string;
  source: string;
  blocked: string;
  impact: string;
  nextStep: string;
  dotClass: string;
};

export function buildSourceImpactRows(
  missing: ConnectorStatus[],
  stale: ConnectorStatus[],
  outsideDailyScope: ConnectorStatus[]
): SourceImpactRow[] {
  const missingRows = missing.map((connector) => ({
    id: `missing-${connector.id}`,
    source: connector.label,
    blocked: sourceBlockedDecisionLabel(connector),
    impact: sourceDecisionImpactLabel(connector),
    nextStep: sourceRepairStepLabel(connector),
    dotClass: "bg-risk"
  }));
  const staleRows = stale.map((connector) => ({
    id: `stale-${connector.id}`,
    source: connector.label,
    blocked: sourceStaleDecisionLabel(connector),
    impact: "Decyzja wymaga świeżego odczytu przed wnioskiem",
    nextStep: "Odśwież źródło przed decyzją",
    dotClass: "bg-wait"
  }));
  const outsideRow =
    outsideDailyScope.length > 0
      ? [
          {
            id: "outside-daily-scope",
            source: "Inne poza zakresem",
            blocked: `Dane z ${outsideDailyScope.length} ${pluralize(
              outsideDailyScope.length,
              "źródła",
              "źródeł",
              "źródeł"
            )} pomijane w dziennym zakresie`,
            impact: "Ograniczony wgląd w nieujęte kanały",
            nextStep: "Zostaw poza planem dnia albo włącz zakres",
            dotClass: "bg-wait"
          }
        ]
      : [];
  if (missingRows.length === 0 && staleRows.length === 0 && outsideRow.length === 0) {
    return [
      {
        id: "sources-ready",
        source: "Brak krytycznych braków",
        blocked: "Główne źródła mogą zasilać decyzje po sprawdzeniu świeżości danych",
        impact: "Decyzje nie są blokowane przez dostęp",
        nextStep: "Pracuj dalej i pilnuj świeżości",
        dotClass: "bg-success"
      }
    ];
  }
  return [...missingRows, ...staleRows, ...outsideRow];
}

function sourceBlockedDecisionLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  const label = connector.label;
  if (id.includes("linkedin")) return "Reklamy LinkedIn, zasięgi, zaangażowanie, leady";
  if (id.includes("facebook")) return "Posty, zasięgi, zaangażowanie, wyniki kampanii";
  if (id.includes("google_ads")) return "Kampanie, rekomendacje, search terms i bezpieczne akcje Ads";
  if (id.includes("analytics") || id.includes("ga4")) return "Ocena jakości ruchu, konwersji i zdarzeń";
  if (id.includes("merchant")) return "Feed produktowy, status produktów i widoczność Shopping/PMax";
  if (id.includes("wordpress")) return "Treści, publikacje i sprawdzenie istniejących stron";
  return `${label}: decyzje zależne od tego źródła`;
}

function sourceDecisionImpactLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  if (id.includes("linkedin")) return "Brak pełnego obrazu działań w kanałach B2B";
  if (id.includes("facebook")) return "Niepełna ocena skuteczności komunikacji";
  if (id.includes("google_ads")) return "Blokada pełnej oceny Ads i zmian kampanii";
  if (id.includes("analytics") || id.includes("ga4")) return "Nie wolno oceniać efektu kampanii bez pomiaru";
  if (id.includes("merchant")) return "Nie wolno oceniać gotowości produktów bez danych pliku produktowego";
  if (id.includes("wordpress")) return "Ryzyko duplikacji i pracy na nieaktualnym spisie treści";
  return "Decyzje z tego kanału pozostają zablokowane albo zdegradowane";
}

function sourceRepairStepLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  if (id.includes("linkedin")) return "Podłącz LinkedIn albo zostaw social jako review-only";
  if (id.includes("facebook")) return "Podłącz Facebook Pages albo pomiń ten kanał";
  if (id.includes("google_ads")) return "Uzupełnij dostęp Ads i odśwież źródło";
  if (id.includes("analytics") || id.includes("ga4")) return "Uzupełnij GA4 i sprawdź pomiar";
  if (id.includes("merchant")) return "Uzupełnij Merchant i odśwież feed";
  if (id.includes("wordpress")) return "Uzupełnij WordPress i pobierz spis treści";
  return "Uzupełnij dostęp i odśwież źródło";
}

function sourceStaleDecisionLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  if (id.includes("google_ads")) return "Aktualna ocena kampanii, kosztów i rekomendacji";
  if (id.includes("analytics") || id.includes("ga4")) return "Aktualna ocena jakości ruchu i pomiaru";
  if (id.includes("merchant")) return "Aktualny status pliku produktowego, produktów i atrybutów";
  if (id.includes("search_console")) return "Aktualne decyzje SEO z GSC";
  if (id.includes("wordpress")) return "Aktualny spis treści i ryzyko duplikacji";
  if (id.includes("ahrefs")) return "Aktualne luki SEO i konkurencja";
  if (id.includes("localo")) return "Aktualna widoczność lokalna";
  return `${connector.label}: decyzje wymagają świeżego odczytu`;
}

export function formatConnectorList(connectors: ConnectorStatus[]) {
  if (connectors.length === 1) return connectors[0].label;
  if (connectors.length === 2) return `${connectors[0].label} i ${connectors[1].label}`;
  return `${connectors.slice(0, -1).map((connector) => connector.label).join(", ")} i ${
    connectors[connectors.length - 1].label
  }`;
}

export function pluralize(count: number, one: string, few: string, many: string) {
  if (count === 1) return one;
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return few;
  return many;
}
