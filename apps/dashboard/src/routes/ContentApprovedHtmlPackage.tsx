import { useState } from "react";

import { getContentWorkItemRevisionHtmlPackage } from "../lib/api";

export function ContentApprovedHtmlPackage({
  workItemId,
  revisionId,
  revisionDigest
}: {
  workItemId: string;
  revisionId: string;
  revisionDigest: string;
}) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloaded, setDownloaded] = useState(false);

  const download = async () => {
    setIsDownloading(true);
    setError(null);
    try {
      const response = await getContentWorkItemRevisionHtmlPackage(workItemId, revisionId);
      if (
        response.manifest.work_item_id !== workItemId ||
        response.manifest.revision_id !== revisionId ||
        response.manifest.content_digest !== revisionDigest
      ) {
        throw new Error("Odebrana paczka nie odpowiada zatwierdzonej rewizji.");
      }
      const url = URL.createObjectURL(new Blob([response.html_document], { type: "text/html;charset=utf-8" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = response.file_name;
      anchor.click();
      URL.revokeObjectURL(url);
      setDownloaded(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Nie udało się przygotować paczki HTML.");
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="mt-4 rounded-xl border border-action/20 bg-action/5 p-4" data-testid="content-approved-html-package">
      <p className="text-sm font-semibold text-ink">Paczka HTML do odbioru</p>
      <p className="mt-1 text-sm leading-6 text-slate-700">Pobierasz zatwierdzoną rewizję wraz z identyfikatorem, digestem i lineage. To nie tworzy draftu WordPress.</p>
      <button type="button" className="mt-3 rounded-md bg-action px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50" disabled={isDownloading} onClick={() => void download()}>
        {isDownloading ? "Przygotowuję paczkę HTML…" : "Pobierz paczkę HTML"}
      </button>
      {downloaded ? <p className="mt-2 text-sm font-semibold text-action">Paczka HTML została pobrana.</p> : null}
      {error ? <p className="mt-2 text-sm font-semibold text-wait">{error}</p> : null}
    </div>
  );
}
