import type { ResearchPacketV2PreviewRecord } from "@wilq/shared-schemas";

export function ResearchPacketReviewDetails({
  record,
  checked,
  onCheckedChange
}: {
  record: ResearchPacketV2PreviewRecord;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  const packet = record.snapshot;

  return (
    <section className="mt-3 rounded-md border border-line bg-slate-50 p-3 leading-5 text-slate-700" aria-label="Pełny pakiet badawczy">
      <p className="font-semibold text-ink">Pakiet do dokładnego przeglądu</p>
      <dl className="mt-2 grid gap-2 sm:grid-cols-2">
        <div><dt className="font-medium">Czytelnik</dt><dd>{packet.planning_context.target_reader}</dd></div>
        <div><dt className="font-medium">Intencja</dt><dd>{packet.planning_context.search_intent}</dd></div>
        <div><dt className="font-medium">Problem</dt><dd>{packet.planning_context.buyer_problem}</dd></div>
        <div><dt className="font-medium">Sygnał do działania</dt><dd>{packet.planning_context.buyer_trigger}</dd></div>
      </dl>
      <h3 className="mt-4 font-semibold text-ink">Fakty wybrane ze sprawdzonych źródeł</h3>
      <ol className="mt-2 space-y-3">
        {packet.selected_facts.map((fact) => (
          <li key={fact.source_fact_id} className="rounded border border-line bg-white p-2">
            <p className="text-slate-600">ID faktu: <code>{fact.source_fact_id}</code></p>
            <p className="whitespace-pre-wrap break-words">{fact.text}</p>
            <p className="mt-1 break-all text-slate-600">Źródło: {fact.source_reference}</p>
            <p className="text-slate-600">Typ źródła: {fact.source_type}</p>
            <p className="text-slate-600">Odczyty: {fact.source_connectors.join(", ")}</p>
            <p className="text-slate-600">Aktualność źródła: {fact.freshness_date}</p>
            <p className="break-all text-slate-600">Dowody: {fact.evidence_ids.join(", ")}</p>
          </li>
        ))}
      </ol>
      {packet.regulatory_profile_id && packet.regulatory_profile_version ? (
        <p className="mt-4 text-slate-600">
          Profil: {packet.regulatory_profile_id}, wersja {packet.regulatory_profile_version}
        </p>
      ) : null}
      {packet.legal_requirements.length > 0 ? (
        <>
          <h3 className="mt-4 font-semibold text-ink">Wymagania prawne powiązane z faktami</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {packet.legal_requirements.map((item) => (
              <li key={item.requirement_id}>
                {item.label}
                <p className="break-all text-slate-600">
                  Fakty: {item.source_fact_ids.join(", ")} · Dowody: {item.evidence_ids.join(", ")}
                </p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {packet.cta_direction ? <p className="mt-4">Kierunek wezwania do działania: {packet.cta_direction}</p> : null}
      {packet.minimum_cta_blocks ? (
        <p className="text-slate-600">Minimalna liczba bloków CTA: {packet.minimum_cta_blocks}</p>
      ) : null}
      {packet.required_cta_patterns?.length ? (
        <p className="text-slate-600">Wymagane wzorce CTA: {packet.required_cta_patterns.join(", ")}</p>
      ) : null}
      {packet.internal_links.length > 0 ? (
        <section className="mt-3" aria-label="Linki wewnętrzne do sprawdzenia">
          <h3 className="font-semibold text-ink">Linki wewnętrzne do sprawdzenia</h3>
          <ul>{packet.internal_links.map((link) => (
            <li key={link.target_url} className="mt-1">
              <p>{link.anchor_hint}: {link.target_url}</p>
              <p className="break-all text-slate-600">Dowody linku: {link.evidence_ids.join(", ")}</p>
            </li>
          ))}</ul>
        </section>
      ) : null}
      <p className="mt-3 break-all text-slate-600">
        Dowody całego pakietu: {packet.evidence_ids.join(", ")}
      </p>
      <details className="mt-3">
        <summary>Dokładne identyfikatory pakietu</summary>
        <p className="break-all">Pakiet: {record.preview_hash}</p>
        <p className="break-all">Źródła: {packet.source_pack_hash}</p>
      </details>
      <label className="mt-4 flex items-start gap-2 font-medium text-ink">
        <input
          type="checkbox"
          checked={checked}
          onChange={(event) => onCheckedChange(event.target.checked)}
          className="mt-1"
        />
        <span>Przeczytałem cały pakiet, fakty źródłowe i wymagania prawne przed decyzją.</span>
      </label>
    </section>
  );
}
