export function ContentWorkbenchHeader() {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-3xl font-semibold tracking-normal text-ink">Treści: praca nad stroną</h1>
        <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-600">
          Publiczna strona, sygnały SEO, sekcje ACF i edytor szkicu w jednym miejscu.
        </p>
      </div>
      <div className="flex gap-2">
        <button type="button" className="inline-flex h-11 items-center gap-2 rounded-md border border-line bg-white px-4 text-sm font-semibold text-ink">
          Dzisiaj
        </button>
        <button type="button" className="inline-flex h-11 items-center gap-2 rounded-md border border-line bg-white px-4 text-sm font-semibold text-ink" onClick={() => window.location.reload()}>
          Odśwież
        </button>
      </div>
    </div>
  );
}
