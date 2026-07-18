import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  ListChecks,
  RefreshCw,
  ShieldAlert
} from "lucide-react";

import { BlockerNotice, LoadingBand } from "../components/OperatorPrimitives";
import {
  BlockerPanel,
  CompactStatTile,
  DashboardToolbar,
  DenseQueueTable,
  PriorityBadge,
  SourceFreshnessStrip,
  StatusPill
} from "../components/DashboardMockupPrimitives";
import { CommandCenterResponse, getCommandCenter, type WorkOrder } from "../lib/api";

function ErrorState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <BlockerNotice message="Nie udało się połączyć z WILQ." />
    </main>
  );
}

export function CommandCenter() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["command-center"],
    queryFn: getCommandCenter
  });

  if (isLoading) return <LoadingBand />;
  if (error || !data) return <ErrorState />;

  const workOrders = data.work_orders;
  const activeOrders = workOrders.filter((item) => item.status !== "done");
  const blockedOrders = workOrders.filter((item) => item.status === "blocked");
  const staleOrders = workOrders.filter((item) => item.freshness.state === "stale");
  const topWork = workOrders[0];
  const forbiddenClaims = uniqueLabels(workOrders.flatMap((item) => item.blocked_claim_labels));

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="lg:hidden">
        <MobileDailyTriage
          item={topWork}
          blockers={blockerRows(data, blockedOrders)}
          forbiddenClaims={forbiddenClaims}
        />
      </div>
      <div className="hidden lg:block">
      <DashboardToolbar
        title="Dzisiaj"
        description="Twoje dzienne centrum operacyjne. Skup się na tym, co ma największy wpływ."
        dateLabel="Dzisiaj"
        onRefresh={() => void refetch()}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <CompactStatTile
          value={activeOrders.length}
          label="decyzje"
          actionLabel="Wymagają Twojej decyzji"
          tone="blue"
          icon={<CheckCircle2 aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={blockedOrders.length}
          label="blokady krytyczne"
          actionLabel="Zatrzymują pracę"
          tone="red"
          icon={<AlertTriangle aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={data.action_ids.length}
          label="akcji do sprawdzenia"
          actionLabel="Zadania do wykonania"
          tone="amber"
          icon={<ListChecks aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={staleOrders.length}
          label="źródła wymagają odświeżenia"
          actionLabel="Dane są nieświeże"
          tone="purple"
          icon={<RefreshCw aria-hidden="true" size={22} />}
        />
      </div>

      <div className="mt-4">
        <SourceFreshnessStrip
          items={workOrders.slice(0, 4).map((item) => ({
            label: item.route_label || item.domain,
            detail: item.freshness_label || item.freshness.state,
            tone: freshnessTone(item.freshness.state),
            icon: <Database aria-hidden="true" size={16} />
          }))}
        />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_0.9fr]">
        {topWork ? <NextBestWorkCard item={topWork} /> : <EmptyWorkCard />}
        <BlockerPanel
          title="Blokady, których nie obchodź"
          badgeLabel={blockedOrders.length > 0 ? `${blockedOrders.length} krytyczne` : undefined}
          items={blockerRows(data, blockedOrders)}
          footer={<ForbiddenClaimsInline claims={forbiddenClaims.slice(0, 4)} />}
        />
      </div>

      <div className="mt-5">
        <DenseQueueTable
          title="Kolejka dziś"
          rows={workOrders}
          getRowKey={(item) => item.id}
          selectedRowKey={topWork?.id}
          emptyLabel="Brak zleceń pracy na dziś."
          columns={[
            {
              key: "priority",
              header: "Priorytet",
              render: (item) => <PriorityBadge value={priorityBadge(item.priority)} />
            },
            {
              key: "area",
              header: "Obszar",
              render: (item) => item.route_label || item.domain
            },
            {
              key: "decision",
              header: "Decyzja",
              render: (item) => item.title
            },
            {
              key: "proof",
              header: "Dowody",
              render: (item) => item.evidence_summary || `${item.evidence_ids.length} dowodów`
            },
            {
              key: "status",
              header: "Status",
              render: (item) => (
                <StatusPill label={item.status_label} tone={statusTone(item.status)} />
              )
            },
            {
              key: "next",
              header: "Następny krok",
              render: (item) => (
                <Link to={item.route} className="font-medium text-action hover:underline">
                  {nextStepLabel(item)}
                </Link>
              )
            }
          ]}
        />
      </div>
      </div>
    </main>
  );
}

function MobileDailyTriage({
  item,
  blockers,
  forbiddenClaims
}: {
  item: WorkOrder | undefined;
  blockers: ReturnType<typeof blockerRows>;
  forbiddenClaims: string[];
}) {
  const visibleBlockers = blockers.slice(0, 2);
  const remainingBlockers = blockers.slice(2);
  const visibleForbiddenClaims = forbiddenClaims.slice(0, 2);
  const remainingForbiddenClaims = forbiddenClaims.slice(2);
  return (
    <section aria-label="Mobilny triage dnia" className="space-y-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Dzisiaj · triage</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">Jedna praca na teraz</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Najpierw wykonaj ten krok. Resztę kolejki otworzysz później.
        </p>
      </div>
      {item ? (
        <article className="rounded-md border border-action/30 bg-white p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-normal text-action">Następna praca</p>
              <h2 className="mt-2 text-lg font-semibold leading-6 text-ink">{item.title}</h2>
            </div>
            <PriorityBadge value={priorityBadge(item.priority)} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">Powód: {item.summary}</p>
          <p className="mt-3 text-sm font-semibold leading-6 text-ink">{item.next_safe_step}</p>
          <Link
            to={item.route}
            className="mt-4 inline-flex h-11 w-full items-center justify-center rounded-md bg-action px-4 text-sm font-semibold text-white"
          >
            Otwórz tę pracę
          </Link>
        </article>
      ) : (
        <BlockerNotice message="Brak zlecenia pracy z WILQ API." />
      )}
      <div className="rounded-md border border-wait/30 bg-wait/10 p-4">
        <h2 className="text-sm font-semibold text-ink">Dwa najważniejsze blokery</h2>
        <ul className="mt-3 space-y-3">
          {visibleBlockers.map((blocker) => (
            <li key={blocker.title} className="text-sm leading-5 text-slate-700">
              <span className="font-semibold text-ink">{blocker.title}</span>
              <span className="mt-1 block">{blocker.description}</span>
            </li>
          ))}
        </ul>
        {remainingBlockers.length ? (
          <details className="mt-3 border-t border-wait/20 pt-3 text-sm text-slate-700">
            <summary className="cursor-pointer font-semibold text-action">
              Pozostałe blokady: {remainingBlockers.length}
            </summary>
            <ul className="mt-3 space-y-3">
              {remainingBlockers.map((blocker) => (
                <li key={blocker.title}>
                  <span className="font-semibold text-ink">{blocker.title}</span>
                  <span className="mt-1 block">{blocker.description}</span>
                </li>
              ))}
            </ul>
          </details>
        ) : null}
        {visibleForbiddenClaims.length ? (
          <p className="mt-3 border-t border-wait/20 pt-3 text-xs leading-5 text-slate-600">
            Nie obiecuj dziś: {visibleForbiddenClaims.join("; ")}
          </p>
        ) : null}
        {remainingForbiddenClaims.length ? (
          <details className="mt-2 text-xs leading-5 text-slate-600">
            <summary className="cursor-pointer font-semibold text-action">
              Pozostałe ograniczenia: {remainingForbiddenClaims.length}
            </summary>
            <p className="mt-2">{remainingForbiddenClaims.join("; ")}</p>
          </details>
        ) : null}
      </div>
    </section>
  );
}

function NextBestWorkCard({ item }: { item: WorkOrder }) {
  return (
    <section className="overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="flex min-h-12 items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold text-ink">Następna najlepsza praca</h2>
        <StatusPill label={`Priorytet ${priorityBadge(item.priority)}`} tone="blue" />
      </div>
      <div className="p-4">
        <div className="flex items-start gap-4">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-blue-100 text-action">
            <ListChecks aria-hidden="true" size={20} />
          </div>
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-ink">{item.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">{item.summary}</p>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <EvidenceBox label="Dowód" value={item.evidence_summary || `${item.evidence_ids.length} dowodów`} />
          <EvidenceBox label="Akcja" value={item.action_summary || `${item.action_ids.length} akcji`} />
        </div>

        <h4 className="mt-5 text-sm font-semibold text-ink">Najbezpieczniejszy następny krok</h4>
        <p className="mt-2 text-sm leading-6 text-slate-700">{item.next_safe_step}</p>

        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            to={item.route}
            className="inline-flex h-10 items-center rounded-md bg-action px-4 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            Otwórz pracę
          </Link>
          <details className="inline-flex">
            <summary className="inline-flex h-10 cursor-pointer items-center rounded-md border border-action/30 px-4 text-sm font-semibold text-action hover:bg-action/10">
              Pokaż dowody
            </summary>
            <p className="mt-3 max-w-xl rounded-md border border-line bg-slate-50 p-3 text-sm leading-6 text-slate-700">
              {item.source_connector_labels.join(", ") || "Brak nazw źródeł"} · {item.close_condition}
            </p>
          </details>
        </div>
      </div>
    </section>
  );
}

function EmptyWorkCard() {
  return (
    <section className="rounded-md border border-line bg-white p-4 shadow-sm">
      <h2 className="text-base font-semibold text-ink">Następna najlepsza praca</h2>
      <p className="mt-2 text-sm leading-6 text-slate-700">
        Brak zleceń pracy z WILQ API. Odśwież źródła albo sprawdź status systemu.
      </p>
    </section>
  );
}

function EvidenceBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-slate-50 px-3 py-3">
      <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-700">{value}</div>
    </div>
  );
}

function ForbiddenClaimsInline({ claims }: { claims: string[] }) {
  if (claims.length === 0) {
    return (
      <p className="text-sm leading-6 text-slate-700">
            Brak dodatkowych zablokowanych twierdzeń w kolejce dnia. Nadal trzymaj się dowodów.
      </p>
    );
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-ink">Nie wolno dziś twierdzić</h3>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {claims.map((claim) => (
          <div key={claim} className="flex items-center gap-2 text-sm text-slate-700">
            <ShieldAlert aria-hidden="true" size={16} className="text-amber-600" />
            <span>{claim}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function blockerRows(data: CommandCenterResponse, blockedOrders: WorkOrder[]) {
  if (blockedOrders.length > 0) {
    return blockedOrders.map((item) => ({
      title: item.title,
      description: item.next_safe_step,
      href: item.route,
      tone: "red" as const
    }));
  }

  if (data.blocker_count > 0) {
    return [
      {
        title: `${data.blocker_count} blokady w danych WILQ`,
        description: "Sprawdź kolejkę i nie wyciągaj końcowych wniosków bez dowodów.",
        href: "/opportunities",
        tone: "red" as const
      }
    ];
  }

  return [
    {
      title: "Brak krytycznych blokad w kolejce dnia",
      description: "Możesz przejść do pierwszej pracy, nadal bez omijania review.",
      tone: "green" as const
    }
  ];
}

function priorityBadge(priority: number): "P1" | "P2" | "P3" | "-" {
  if (priority <= 10) return "P1";
  if (priority <= 20) return "P2";
  if (priority <= 40) return "P3";
  return "-";
}

function statusTone(status: WorkOrder["status"]) {
  if (status === "done") return "green";
  if (status === "blocked") return "red";
  return "amber";
}

function freshnessTone(state: WorkOrder["freshness"]["state"]) {
  if (state === "fresh") return "green";
  if (state === "stale") return "amber";
  if (state === "missing") return "red";
  return "neutral";
}

function nextStepLabel(item: WorkOrder) {
  if (item.route_label) return `Otwórz ${item.route_label}`;
  return "Otwórz pracę";
}

function uniqueLabels(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)));
}
