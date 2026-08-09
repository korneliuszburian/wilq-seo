import { type ConnectorStatus, type Workflow, type WorkflowRun } from "../lib/api";
import { SourceStatTile } from "./SettingsSections";

export function SystemSurfaceSections({
  connectors,
  workflows,
  workflowRuns
}: {
  connectors: ConnectorStatus[];
  workflows: Workflow[];
  workflowRuns: WorkflowRun[];
}) {
  const technicalReviewCount = workflows.filter((workflow) =>
    workflow.status !== "ready" || workflow.risk !== "low"
  ).length;
  const blockedSecurityRules = systemSecurityRows().filter((row) => row.status === "blocked").length;
  const activeConnectors = connectors.filter((connector) => connector.configured).length;
  const workflowLabels = new Map(workflows.map((workflow) => [workflow.id, workflow.label]));

  return (
    <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SourceStatTile value={workflows.length} label="procesów" tone="default" />
        <SourceStatTile value={workflowRuns.length} label="ostatnie uruchomienia" tone="default" />
        <SourceStatTile value={technicalReviewCount} label="obszary techniczne w review" tone="wait" />
        <SourceStatTile value={blockedSecurityRules} label="blokady systemowe" tone="risk" />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <article className="rounded-md border border-line bg-white">
          <SystemPanelHeader title="Procesy" cta="Zobacz wszystkie" href="/workflows" />
          <div className="divide-y divide-line">
            {workflows.slice(0, 3).map((workflow) => (
              <SystemListRow
                key={workflow.id}
                title={workflow.label}
                description={workflow.description}
                status={workflow.status === "ready" ? "gotowe" : workflow.status_label ?? workflow.status}
                statusClass={workflow.status === "ready" ? "bg-success/10 text-success" : "bg-wait/10 text-wait"}
              />
            ))}
          </div>
          <div className="border-t border-line px-4 py-3 text-sm text-slate-600">
            Łącznie {workflows.length} procesów
          </div>
        </article>

        <article className="rounded-md border border-line bg-white">
          <SystemPanelHeader title="Uruchomienia Codex" cta="Zobacz wszystkie" href="/codex-runs" />
          <div className="divide-y divide-line">
            {workflowRuns.slice(0, 3).map((run) => (
              <SystemListRow
                key={run.id}
                title={workflowLabels.get(run.workflow_id) ?? "Proces WILQ"}
                description={formatSystemRunDescription(run)}
                status={run.status_label}
                statusClass={run.status === "failed" ? "bg-risk/10 text-risk" : "bg-success/10 text-success"}
              />
            ))}
            {workflowRuns.length === 0 ? (
              <div className="px-4 py-3 text-sm text-slate-600">
                Brak zapisanych uruchomień do pokazania.
              </div>
            ) : null}
          </div>
          <div className="border-t border-line px-4 py-3">
            <a href="/codex-runs" className="text-sm font-semibold text-action">
              Zobacz historię uruchomień
            </a>
          </div>
        </article>

        <article className="rounded-md border border-line bg-white">
          <SystemPanelHeader title="Bezpieczeństwo" cta="Zobacz wszystkie" href="/security" />
          <div className="divide-y divide-line">
            {systemSecurityRows().map((row) => (
              <SystemListRow
                key={row.title}
                title={row.title}
                description={row.description}
                status={row.status === "active" ? "aktywna" : "zablokowana"}
                statusClass={row.status === "active" ? "bg-success/10 text-success" : "bg-risk/10 text-risk"}
              />
            ))}
          </div>
          <div className="border-t border-line px-4 py-3">
            <a href="/security" className="text-sm font-semibold text-action">
              Zobacz reguły bezpieczeństwa
            </a>
          </div>
        </article>
      </section>

      <section className="rounded-md border border-line bg-white">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-base font-semibold text-ink">Eksperymentalne obszary</h2>
          <p className="mt-1 text-sm text-slate-600">
            Obszary w fazie testów lub z ograniczonym dostępem.
          </p>
        </div>
        <div className="grid gap-3 p-4 xl:grid-cols-2">
          <SystemExperimentCard
            title="Posty społecznościowe"
            status="w review"
            description="Publikacja i harmonogram treści w social media."
            note="Obszar w weryfikacji. Trwają testy integracji i zasad odpowiedzialności."
          />
          <SystemExperimentCard
            title="Eksporty Google Sheets"
            status="zablokowany"
            description="Eksport danych i raportów do arkuszy Google."
            note="Nie spełnia standardów bezpieczeństwa. Eksporty zewnętrzne wyłączone."
            blocked
          />
        </div>
      </section>

      <section className="rounded-md border border-line bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
          <div>
            <h2 className="text-base font-semibold text-ink">Szczegóły techniczne</h2>
            <p className="mt-1 text-sm text-slate-600">
              Podstawowe informacje systemowe i dostępność.
            </p>
          </div>
          <a
            href="/settings"
            className="rounded-md border border-action/30 px-4 py-2 text-sm font-semibold text-action"
          >
            Zobacz szczegóły techniczne
          </a>
        </div>
        <div className="grid divide-y divide-line text-sm md:grid-cols-2 md:divide-x md:divide-y-0">
          <div className="grid divide-y divide-line">
            <SystemDetailRow label="Adaptery" value={`${activeConnectors} aktywnych`} />
            <SystemDetailRow label="Logi" value="ostatnie uruchomienia dostępne w audycie" />
          </div>
          <div className="grid divide-y divide-line">
            <SystemDetailRow label="Runtime" value="lokalny WILQ API i dashboard" />
            <SystemDetailRow label="Role" value="marketer mode + technical audit mode" />
          </div>
        </div>
      </section>
    </>
  );
}

function SystemPanelHeader({ title, cta, href }: { title: string; cta: string; href: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      <a href={href} className="rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-action">
        {cta}
      </a>
    </div>
  );
}

function SystemListRow({
  title,
  description,
  status,
  statusClass
}: {
  title: string;
  description: string;
  status: string;
  statusClass: string;
}) {
  return (
    <div className="flex items-start justify-between gap-3 px-4 py-3">
      <div>
        <div className="text-sm font-semibold text-ink">{title}</div>
        <p className="mt-1 line-clamp-2 text-sm leading-6 text-slate-600">{description}</p>
      </div>
      <span className={`shrink-0 rounded px-2 py-1 text-xs font-semibold ${statusClass}`}>
        {status}
      </span>
    </div>
  );
}

function SystemExperimentCard({
  title,
  status,
  description,
  note,
  blocked = false
}: {
  title: string;
  status: string;
  description: string;
  note: string;
  blocked?: boolean;
}) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
        </div>
        <span className={`rounded px-2 py-1 text-xs font-semibold ${blocked ? "bg-risk/10 text-risk" : "bg-wait/10 text-wait"}`}>
          {status}
        </span>
      </div>
      <p className={`mt-4 rounded-md border p-3 text-sm leading-6 ${
        blocked
          ? "border-risk/30 bg-risk/10 text-risk"
          : "border-action/30 bg-action/5 text-slate-700"
      }`}
      >
        {note}
      </p>
    </article>
  );
}

function SystemDetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[160px_1fr] gap-3 px-4 py-3">
      <div className="font-semibold text-ink">{label}</div>
      <div className="text-slate-600">{value}</div>
    </div>
  );
}

function systemSecurityRows() {
  return [
    {
      title: "Brak zapisu zmian bez audytu",
      description: "Zmiany zapisywane tylko po audycie.",
      status: "active"
    },
    {
      title: "Brak rekomendacji bez dowodów",
      description: "Rekomendacje muszą mieć dowody.",
      status: "active"
    },
    {
      title: "Zapis zmian zawsze z dowodami",
      description: "Każdy zapis wymaga źródeł i uzasadnienia.",
      status: "active"
    },
    {
      title: "Blokada bez kontekstu",
      description: "Blokada bez wyjaśnienia jest zabroniona.",
      status: "active"
    },
    {
      title: "Brak pobrań z kontekstem",
      description: "WILQ nie może pobrać Social Context-Pack.",
      status: "blocked"
    }
  ] as const;
}

function formatSystemRunDescription(run: WorkflowRun) {
  const timestamp = new Date(run.started_at).toLocaleString("pl-PL", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  });
  return `${timestamp} · Operator: System`;
}
