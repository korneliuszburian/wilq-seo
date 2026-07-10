import { ShieldCheck } from "lucide-react";

import { MetricTile } from "../components/OperatorPrimitives";

export type CompactRouteConfig = {
  title: string;
  description: string;
  status: string;
  nextStep: string;
  blockers: string[];
  safeRoute?: string;
};

const COMPACT_ROUTE_CONFIGS: Record<string, CompactRouteConfig> = {
  "/ads-doctor/search-terms": {
    title: "Search terms",
    description:
      "Ten drilldown jest ukryty z głównej nawigacji, dopóki nie ma osobnej kolejki wyszukiwanych haseł. Bezpieczny przegląd haseł jest prowadzony w widoku Reklamy i pomiar.",
    status: "ukryty placeholder",
    nextStep:
      "Otwórz Reklamy i pomiar, sprawdź kolejkę diagnostyczną i dopiero stamtąd przejdź do review haseł albo wykluczeń.",
    blockers: [
      "brakuje samodzielnej kolejki search terms w marketer-mode",
      "propozycje wykluczeń wymagają kontekstu 90 dni, intencji i podglądu zmian",
      "nie wolno twierdzić zmarnowanego budżetu ani CPA/ROAS bez brakujących kontraktów"
    ],
    safeRoute: "/ads-doctor"
  },
  "/ads-doctor/scaling": {
    title: "Skalowanie Ads",
    description:
      "Skalowanie kampanii nie jest osobnym gotowym widokiem. WILQ nie powinien proponować zwiększania budżetu bez strategii, pomiaru i review.",
    status: "zablokowane do czasu reguł skalowania",
    nextStep:
      "Najpierw sprawdź Reklamy i pomiar: budżety, pomiar GA4, rekomendacje i blokady strategii. Skalowanie zostaje review-only.",
    blockers: [
      "brakuje zatwierdzonego celu biznesowego i guardrail budżetu",
      "brakuje kontraktów przed/po zmianie oraz human strategy review",
      "nie ma bezpiecznego ActionObject do zmiany budżetu"
    ],
    safeRoute: "/ads-doctor"
  },
  "/ads-doctor/seasonality": {
    title: "Sezonowość Ads",
    description:
      "Sezonowość wymaga porównań okresów i kontekstu biznesowego. Ten placeholder nie może udawać wniosku o spadkach albo trendach.",
    status: "ukryty placeholder",
    nextStep:
      "Użyj Reklamy i pomiar do bieżącej diagnostyki. Wniosek sezonowy dodaj dopiero po dostępnych porównaniach okresów i źródłach pomiaru.",
    blockers: [
      "brakuje porównania rok do roku i okres do okresu",
      "brakuje kontraktu zmiany sezonowej oraz kontekstu świąt/promocji",
      "nie wolno tłumaczyć spadków sezonowością bez dowodów"
    ],
    safeRoute: "/ads-doctor"
  },
  "/ads-doctor/recommendations": {
    title: "Rekomendacje Ads",
    description:
      "Rekomendacje Google Ads są review-only i nie powinny być osobnym pustym ekranem. WILQ może przygotować kolejkę sprawdzenia, ale nie przyjmuje rekomendacji automatycznie.",
    status: "review-only",
    nextStep:
      "Otwórz Reklamy i pomiar, sprawdź rekomendacje w kolejce diagnostycznej i zatwierdzaj tylko po preview oraz review operatora.",
    blockers: [
      "brakuje zgody na zapis rekomendacji",
      "Google preview nie jest obietnicą poprawy wyniku",
      "zmiany budżetu i strategii stawek wymagają osobnego review"
    ],
    safeRoute: "/ads-doctor"
  },
  "/content-inventory": {
    title: "Spis treści",
    description:
      "Skrót obszaru, który docelowo ma pokazywać realne treści z ekologus.pl i sklepu. Dziś decyzje treściowe są prowadzone w widoku treści.",
    status: "w trakcie porządkowania",
    nextStep:
      "Przejdź do widoku treści i sprawdź kolejkę zachowania, odświeżenia, scalenia albo blokady.",
    blockers: [
      "pełny spis treści nie jest jeszcze gotowy",
      "nie ma finalnego sprawdzenia duplikatów i adresów kanonicznych; nie używaj tego widoku do decyzji o pisaniu"
    ],
    safeRoute: "/content-workflow"
  },
  "/google-sheets": {
    title: "Google Sheets",
    description:
      "Miejsce na eksporty i pakiety do pracy operacyjnej. Ten widok nie powinien udawać raportu ani pokazywać pełnego rejestru WILQ.",
    status: "zablokowane do czasu ustalenia bezpiecznego eksportu",
    nextStep:
      "Najpierw wybierz konkretny zakres eksportu: pakiet testowy, lista decyzji, kolejka treści albo dowody do sprawdzenia.",
    blockers: [
      "nie ma zatwierdzonego zakresu eksportu; nie wysyłaj danych poza WILQ",
      "nie ma reguł, które pola mogą trafić do arkusza bez sekretów i technicznych śladów"
    ],
    safeRoute: "/command-center"
  },
  "/codex-runs": {
    title: "Uruchomienia Codex",
    description:
      "Miejsce na historię pracy operatora i sprawdzenia jakości odpowiedzi. Domyślny widok nie pokazuje roboczych poleceń ani pełnych danych technicznych.",
    status: "częściowo dostępne przez zapisane wyniki sprawdzeń",
    nextStep:
      "Sprawdź ostatni zapis postępu, jeśli potrzebujesz potwierdzenia ostatniego przebiegu.",
    blockers: [
      "nie ma osobnego widoku historii uruchomień z oczyszczonymi poleceniami roboczymi",
      "nie ma finalnego podziału na potwierdzenie dla marketera i widok techniczny operatora"
    ]
  },
  "/security": {
    title: "Bezpieczeństwo",
    description:
      "Kontrola zasad bezpieczeństwa WILQ: brak sekretów w UI, brak zapisu zmian bez audytu i brak rekomendacji bez dowodów.",
    status: "zasady aktywne, widok produktowy do dopracowania",
    nextStep:
      "Do weryfikacji użyj aktualnych testów języka, blokad zapisu zmian i zapisanego postępu.",
    blockers: [
      "nie ma pełnego dashboardu bezpieczeństwa; traktuj ten widok jako skrót zasad",
      "nie ma produkcyjnych ról i uprawnień; nie traktuj tego jako modelu dostępu"
    ]
  }
};

export function compactRouteConfig(routeName: string) {
  return COMPACT_ROUTE_CONFIGS[routeName];
}

export function CompactRoutePanel({ config }: { config: CompactRouteConfig }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ShieldCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Status widoku
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">{config.description}</p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <MetricTile label="Status" value={config.status} />
        <MetricTile label="Blokady" value={config.blockers.length} />
        <MetricTile label="Szczegóły systemowe" value="schowane" />
      </div>
      <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-wait">
        <div className="font-semibold">Co zrobić dalej</div>
        <p>{config.nextStep}</p>
      </div>
      {config.blockers.length > 0 ? (
        <div className="mt-4 text-sm leading-6 text-slate-700">
          <div className="font-semibold text-ink">Co jeszcze blokuje gotowość</div>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {config.blockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {config.safeRoute ? (
        <a
          href={config.safeRoute}
          className="mt-4 inline-flex min-h-9 items-center rounded-md border border-action bg-white px-3 py-2 text-xs font-medium text-action hover:bg-action/10"
        >
          Otwórz bezpieczny widok
        </a>
      ) : null}
    </section>
  );
}
