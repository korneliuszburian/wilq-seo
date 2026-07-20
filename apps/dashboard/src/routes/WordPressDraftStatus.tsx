import type { ContentWordPressDraftActivationPacketResponse, ContentWorkItemWordPressDraftExecutionResponse } from "../lib/api";

export function WordPressDraftReadbackStatus({ readback }: { readback: NonNullable<ContentWordPressDraftActivationPacketResponse["draft_readback"]> }) {
  if (readback.status === "blocked") { const blocker = readback.blockers[0]; return <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 px-3 py-2 text-sm leading-6 text-slate-700"><p className="font-semibold text-wait">Odczyt szkicu wymaga sprawdzenia</p><p className="mt-1">{blocker ? `${blocker.label}. ${blocker.next_step}` : "WILQ nie potwierdził jeszcze treści szkicu z dev WordPressa."}</p></div>; }
  const acfNames = readback.acf_field_names.slice(0, 6);
  const editLink = readback.edit_link || readback.link;
  return <div className="mt-3 rounded-md border border-success/25 bg-success/5 px-3 py-3 text-sm leading-6 text-slate-700"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold text-success">Odczyt z dev WordPress</p><p className="mt-1 font-semibold text-ink">{readback.title || "Szkic bez tytułu"} <span className="font-normal text-slate-500">({readback.post_status || "bez statusu"})</span></p></div>{editLink ? <a href={editLink} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center rounded-md border border-success/30 bg-white px-3 text-sm font-semibold text-success">Otwórz szkic w WordPress</a> : null}</div><p className="mt-2">{readback.content_summary || "WordPress zwrócił szkic, ale bez czytelnego streszczenia treści."}</p><div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600"><span className="rounded-md border border-line bg-white px-2 py-1">{readback.content_word_count ?? 0} słów</span><span className="rounded-md border border-line bg-white px-2 py-1">{readback.acf_field_count ?? 0} pól ACF</span>{acfNames.map((name) => <span key={name} className="rounded-md border border-line bg-white px-2 py-1">{name}</span>)}</div></div>;
}

export function WordPressDraftExecutionStatus({ result }: { result: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] }) {
  const tone = result.status === "created" ? "border-success/30 bg-success/10 text-success" : result.status === "blocked" ? "border-risk/30 bg-risk/10 text-risk" : "border-action/30 bg-action/10 text-action";
  return <p className={`mt-3 rounded-md border px-3 py-2 text-sm leading-6 ${tone}`}>{wordpressDraftExecutionStatusText(result)}</p>;
}
export function wordpressDraftExecutionStatusText(result: ContentWorkItemWordPressDraftExecutionResponse["execution_result"]) {
  if (result.status === "created") return `Szkic utworzony na devie jako WordPress draft${result.wordpress_post_id ? `, ID ${result.wordpress_post_id}` : ""}. Publikacja i nadpisywanie pozostają zablokowane.`;
  if (result.status === "blocked") { const blocker = result.blockers[0]; return blocker ? `Zapis zablokowany: ${blocker.label}. ${blocker.next_step}` : "Zapis szkicu został zablokowany przez WILQ."; }
  return "Podgląd szkicu jest gotowy. Zewnętrzny zapis nie został wykonany.";
}
