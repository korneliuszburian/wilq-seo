import type { ReactNode } from "react";
import { Gauge, MousePointerClick, Sparkles, Target } from "lucide-react";

import { StatusPill } from "../../components/DashboardMockupPrimitives";
import type {
  ActionObject,
  AdsDiagnosticsResponse,
  DemandGenReadinessContract,
  Ga4DiagnosticsResponse
} from "../../lib/api";

export function SafeWorkModes({
  data,
  ga4Data,
  demandGenData,
  actions,
  actionsPending
}: {
  data: AdsDiagnosticsResponse;
  ga4Data: Ga4DiagnosticsResponse | null;
  demandGenData: DemandGenReadinessContract | null;
  actions: ActionObject[];
  actionsPending: boolean;
}) {
  const summary = data.operator_summary;

  return (
    <section className="overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold text-ink">Bezpieczne tryby pracy</h2>
        <p className="mt-1 text-sm leading-5 text-slate-600">
          WILQ pokazuje review i podglądy. Nie zapisuje zmian w Ads ani nie odblokowuje obietnic bez bramek.
        </p>
      </div>
      <div className="divide-y divide-line">
        <ModeRow
          icon={<MousePointerClick aria-hidden="true" size={16} />}
          title="Review Ads"
          detail={`${summary.ready_area_count} gotowe obszary, ${summary.blocked_area_count} blokady`}
          statusLabel={summary.operator_review_gate_summary_label || "wymaga review"}
          href="/actions"
        />
        <ModeRow
          icon={<Gauge aria-hidden="true" size={16} />}
          title="Sprawdź pomiar GA4"
          detail={ga4Data?.freshness_assessment.next_step ?? "Brak odczytu GA4 w tym widoku"}
          statusLabel={ga4Data?.action_summary_label ?? "sprawdź GA4"}
          href="/ga4"
        />
        <ModeRow
          icon={<Sparkles aria-hidden="true" size={16} />}
          title="Demand Gen tylko do gotowości"
          detail={demandGenData?.next_step ?? "Brak kontraktu Demand Gen"}
          statusLabel={demandGenData?.action_summary_label ?? "review-only"}
          href="/ads-doctor/demand-gen"
        />
        <ModeRow
          icon={<Target aria-hidden="true" size={16} />}
          title="ActionObject"
          detail={
            actionsPending
              ? "WILQ wczytuje kolejkę bezpiecznych akcji. Zapis pozostaje zablokowany."
              : actions.length > 0
              ? actions[0].human_diagnosis || actions[0].recommended_reason
              : "Brak akcji dla tej powierzchni"
          }
          statusLabel={actionsPending ? "wczytywanie" : data.action_summary_label}
          href={actions[0] ? `/actions/${actions[0].id}` : "/actions"}
        />
      </div>
    </section>
  );
}

function ModeRow({
  icon,
  title,
  detail,
  statusLabel,
  href
}: {
  icon: ReactNode;
  title: string;
  detail: string;
  statusLabel: string;
  href: string;
}) {
  return (
    <a href={href} className="grid gap-2 px-4 py-3 hover:bg-slate-50 sm:grid-cols-[1fr_auto]">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-blue-50 text-action">
          {icon}
        </span>
        <span>
          <span className="block text-sm font-semibold text-ink">{title}</span>
          <span className="mt-0.5 line-clamp-2 block text-sm leading-5 text-slate-600">{detail}</span>
        </span>
      </div>
      <StatusPill label={statusLabel} tone="blue" />
    </a>
  );
}
