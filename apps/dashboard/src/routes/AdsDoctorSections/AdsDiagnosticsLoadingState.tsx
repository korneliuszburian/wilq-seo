import { DashboardToolbar } from "../../components/DashboardMockupPrimitives";

export function AdsDiagnosticsLoadingState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <DashboardToolbar
        title="Reklamy i pomiar"
        description="WILQ pobiera źródłowe dane Ads. Nie pokazuję rekomendacji, dopóki odczyt nie wróci."
        dateLabel="Dzisiaj"
      />
      <section className="rounded-md border border-amber-200 bg-amber-50 p-5 shadow-sm">
        <div className="text-sm font-semibold text-amber-900">Odczyt Ads w toku</div>
        <p className="mt-2 text-sm leading-6 text-amber-800">
          Zapis zmian i wnioski o ROAS, przychodzie, waste oraz konwersjach pozostają zablokowane
          do czasu potwierdzenia danych.
        </p>
      </section>
    </main>
  );
}
