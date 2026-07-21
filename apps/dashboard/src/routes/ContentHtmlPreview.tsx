export function ContentHtmlPreview({
  contentHtml,
  title,
  testId,
  className = "",
  minHeightClass = "min-h-[30rem]"
}: {
  contentHtml: string;
  title: string;
  testId?: string;
  className?: string;
  minHeightClass?: string;
}) {
  return (
    <iframe
      title={title}
      sandbox=""
      srcDoc={previewDocument(contentHtml)}
      data-testid={testId}
      className={`block ${minHeightClass} w-full rounded-md border border-line bg-white ${className}`}
    />
  );
}

function previewDocument(contentHtml: string) {
  return `<!doctype html><html lang="pl"><head><meta charset="utf-8"><style>
    html { color: #1f2937; font: 16px/1.75 ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; padding: 1.25rem; overflow-wrap: anywhere; }
    h3, h4, h5, h6 { color: #172033; line-height: 1.3; }
    a { color: #155eef; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #dbe3ef; padding: .5rem; text-align: left; }
  </style></head><body>${contentHtml}</body></html>`;
}
