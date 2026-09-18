import type { ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import type { DiagnosticDataReadiness } from "@wilq/shared-schemas";

import { DiagnosticDataReadinessPanel } from "./DiagnosticDataReadinessPanel";
import { BlockerNotice, LoadingBand } from "./OperatorPrimitives";

export function DiagnosticPage<TData>({
  query,
  title,
  description,
  unavailableMessage,
  metrics,
  readiness,
  children
}: {
  query: UseQueryResult<TData>;
  title: string;
  description: string;
  unavailableMessage: string;
  metrics?: (data: TData) => ReactNode;
  readiness?: (data: TData) => DiagnosticDataReadiness;
  children: (data: TData) => ReactNode;
}) {
  if (query.isLoading) return <LoadingBand />;
  if (query.error || !query.data) {
    return <DiagnosticSurfaceUnavailable message={unavailableMessage} />;
  }

  return (
    <DiagnosticSurfaceShell
      title={title}
      description={description}
      metrics={metrics ? metrics(query.data) : undefined}
      readiness={readiness ? readiness(query.data) : undefined}
    >
      {children(query.data)}
    </DiagnosticSurfaceShell>
  );
}

export function DiagnosticSurfaceShell({
  title,
  description,
  metrics,
  readiness,
  children
}: {
  title: string;
  description: string;
  metrics?: ReactNode;
  readiness?: DiagnosticDataReadiness;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {description}
          </p>
        </div>
        {metrics}
      </div>
      {readiness ? <DiagnosticDataReadinessPanel readiness={readiness} /> : null}
      {children}
    </main>
  );
}

export function DiagnosticSurfaceUnavailable({ message }: { message: string }) {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <BlockerNotice message={message} />
    </main>
  );
}
