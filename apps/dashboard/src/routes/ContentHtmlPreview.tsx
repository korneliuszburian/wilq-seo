import { useState, type SyntheticEvent } from "react";

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
  const [measurement, setMeasurement] = useState<{
    contentHtml: string;
    height: number;
  } | null>(null);

  const measureHeight = (event: SyntheticEvent<HTMLIFrameElement>) => {
    const document = event.currentTarget.contentDocument;
    if (!document) return;
    const height = Math.max(
      document.body?.scrollHeight ?? 0,
      document.documentElement?.scrollHeight ?? 0,
      document.body?.offsetHeight ?? 0,
      document.documentElement?.offsetHeight ?? 0
    );
    // The iframe border consumes two pixels from its content viewport. Keep
    // that margin so a document that exactly fills its measured height does
    // not gain a cosmetic inner scrollbar.
    if (height > 0) setMeasurement({ contentHtml, height: height + 2 });
  };

  return (
    <iframe
      title={title}
      sandbox="allow-same-origin"
      referrerPolicy="no-referrer"
      srcDoc={previewDocument(contentHtml)}
      data-testid={testId}
      className={`block ${minHeightClass} w-full rounded-md border border-line bg-white ${className}`}
      style={measurement?.contentHtml === contentHtml ? { height: `${measurement.height}px` } : undefined}
      onLoad={measureHeight}
    />
  );
}

function previewDocument(contentHtml: string) {
  return `<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:"><style>
    html { color: #1f2937; font: 16px/1.75 ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; padding: 1.25rem; overflow-wrap: anywhere; }
    h3, h4, h5, h6 { color: #172033; line-height: 1.3; }
    a { color: #155eef; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #dbe3ef; padding: .5rem; text-align: left; }
  </style></head><body>${contentHtml}</body></html>`;
}
