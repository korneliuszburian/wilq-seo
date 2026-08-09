import { ShieldAlert } from "lucide-react";

import { TraceLine } from "../../components/TraceLine";
import type { MerchantDiagnosticsResponse } from "./shared";

export function MerchantFeedSafetyPanel({ data }: { data: MerchantDiagnosticsResponse }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa pliku produktowego
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Merchant Center pozostaje w trybie przeglądu i przygotowania. WILQ może pokazać
              kolejkę problemów, dowody i podgląd zmian, ale nie może zmienić pliku produktowego,
              obiecać ponownego zatwierdzenia produktu ani zapisać zmiany bez sprawdzenia w WILQ i audytu.
            </p>
          </div>
        </div>
        <TraceLine
          label="Nie wolno twierdzić"
          values={data.sections.flatMap((section) => section.blocked_claim_labels)}
        />
      </section>
  );
}

