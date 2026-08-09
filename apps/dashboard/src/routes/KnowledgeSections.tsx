import { type UseQueryResult } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useState } from "react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  type KnowledgeCard,
  type KnowledgeSourceFactView,
  type KnowledgeSourceMaterialView,
  type KnowledgeSourceMaterialReadiness,
  type KnowledgeOperatingMapResponse,
  type MarketingPlaybook
} from "../lib/api";
import { InlineErrorState } from "./ErrorStates";
import {
  KnowledgeCardList,
  KnowledgeSourceFactList,
  KnowledgeSourceMaterialReadinessBanner,
  KnowledgeSourceMaterialSummary,
  KnowledgeOperatingMapPanel,
  PlaybookList
} from "./KnowledgePanels";
import { SectionHeading } from "./SettingsSections";

export function KnowledgeSurfaceSections({
  knowledgeMap,
  knowledgeCards,
  knowledgeSourceFacts,
  knowledgeSourceMaterials,
  knowledgeSourceMaterialReadiness,
  playbooks,
  showKnowledgeMap,
  showKnowledgeCards,
  setShowKnowledgeCards,
  showKnowledgePlaybooks,
  setShowKnowledgePlaybooks
}: {
  knowledgeMap: UseQueryResult<KnowledgeOperatingMapResponse>;
  knowledgeCards: UseQueryResult<KnowledgeCard[]>;
  knowledgeSourceFacts: UseQueryResult<KnowledgeSourceFactView[]>;
  knowledgeSourceMaterials: UseQueryResult<KnowledgeSourceMaterialView[]>;
  knowledgeSourceMaterialReadiness: UseQueryResult<KnowledgeSourceMaterialReadiness>;
  playbooks: UseQueryResult<MarketingPlaybook[]>;
  showKnowledgeMap: boolean;
  showKnowledgeCards: boolean;
  setShowKnowledgeCards: (value: boolean | ((current: boolean) => boolean)) => void;
  showKnowledgePlaybooks: boolean;
  setShowKnowledgePlaybooks: (value: boolean | ((current: boolean) => boolean)) => void;
}) {
  const [showAllSourceMaterials, setShowAllSourceMaterials] = useState(false);
  const map = knowledgeMap.data;
  const cards = knowledgeCards.data ?? [];
  const bindings = map?.bindings ?? [];
  const nearestCard = cards[0];
  const sourceMaterials = knowledgeSourceMaterials.data ?? [];
  const sourceFacts = knowledgeSourceFacts.data ?? [];
  const pendingSourceMaterials = sourceMaterials.filter(
    (material) => material.import_status !== "imported"
  );
  const nearestTitle =
    pendingSourceMaterials[0]?.title ||
    nearestCard?.display_title ||
    nearestCard?.title ||
    bindings[0]?.title ||
    "Materiał źródłowy do review";
  const blockedClaimCount = sourceFacts.reduce(
    (sum, fact) => sum + fact.blocked_claims.length,
    0
  );
  const reviewCount = pendingSourceMaterials.length;
  const allowedClaimCount = sourceFacts.filter(
    (fact) => fact.generation_status === "eligible" && fact.blocked_claims.length === 0
  ).length;
  const reviewClaimCount = sourceFacts.filter(
    (fact) => fact.generation_status !== "eligible" && fact.blocked_claims.length === 0
  ).length;
  const totalClaims = allowedClaimCount + reviewClaimCount + blockedClaimCount;
  const serviceCount = cards.filter((card) => /service|usług|usl|service_profile/i.test(card.card_type)).length;
  const approvedCurrentCount = approvedKnowledgeFactCount(knowledgeSourceFacts.data);
  const pendingMaterialCount = knowledgeSourceMaterials.data?.filter(
    (material) => material.import_status !== "imported"
  ).length ?? 0;

  return (
    <>
      <section className="rounded-xl border border-line bg-slate-50/70 p-4 lg:p-5">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-action">Źródła Ekologusa</p>
            <h2 className="mt-1 text-lg font-semibold text-ink">Realne materiały i fakty Ekologusa</h2>
            <p className="mt-1 text-sm text-slate-600">To jest źródło dla treści. Karty i playbooki poniżej są tylko warstwą operacyjną — nie są transkrypcjami ani wypowiedziami firmy.</p>
          </div>
          <span className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-semibold text-slate-600">{knowledgeSourceFacts.data?.length ?? 0} faktów w rejestrze</span>
        </div>
        {knowledgeSourceFacts.isLoading ? <LoadingBand /> : knowledgeSourceFacts.error ? <InlineErrorState message="Nie udało się pobrać faktów źródłowych." /> : <KnowledgeSourceFactList facts={knowledgeSourceFacts.data ?? []} />}
        {knowledgeSourceMaterialReadiness.isLoading ? <LoadingBand /> : knowledgeSourceMaterialReadiness.error ? <InlineErrorState message="Nie udało się pobrać gotowości korpusu źródłowego." /> : <KnowledgeSourceMaterialReadinessBanner readiness={knowledgeSourceMaterialReadiness.data} />}
        {knowledgeSourceMaterials.isLoading ? <LoadingBand /> : knowledgeSourceMaterials.error ? <InlineErrorState message="Nie udało się pobrać manifestu materiałów." /> : <KnowledgeSourceMaterialSummary materials={knowledgeSourceMaterials.data ?? []} />}
      </section>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KnowledgeStatTile value={cards.length} label="kart" cta="Zobacz wszystkie" />
        <KnowledgeStatTile value={serviceCount} label="usług" cta="Zobacz wszystkie" tone="success" />
        <KnowledgeStatTile value={reviewCount} label="do sprawdzenia" cta="Przejdź do kolejki" tone="wait" />
        <KnowledgeStatTile value={approvedCurrentCount} label="zatwierdzonych faktów" cta="Zobacz zatwierdzone fakty" tone="action" />
      </section>
      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-md border border-line bg-white">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold text-ink">Najbliższy krok źródłowy</h2>
            <span className="rounded bg-wait/10 px-2 py-1 text-xs font-semibold text-wait">
              Wymaga sprawdzenia
            </span>
          </div>
          <div className="p-4">
            <h3 className="text-base font-semibold text-ink">
              {pendingMaterialCount > 0
                ? `Doprowadź ${pendingMaterialCount} materiałów Ekologusa do redakcji i review`
                : `Sprawdź kartę: ${nearestTitle}`}
            </h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-700">
              {pendingMaterialCount > 0
                ? "Manifest i hashe są zapisane, ale tekst nie zasila jeszcze generowania. Najpierw trzeba wprowadzić redagowane fragmenty z kontrolą dostępu i śladem źródła."
                : "Karta ma źródła, ale wymaga decyzji człowieka zanim stanie się zatwierdzoną wiedzą produkcyjną."}
            </p>
            <div className="mt-4">
              <div className="text-sm font-semibold text-ink">Wymagane sprawdzenia</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {[
                  "decyzja właściciela",
                  "źródła są jasne",
                  "twierdzenia sprawdzone",
                  "notatka z decyzji"
                ].map((label) => (
                  <span
                    key={label}
                    className="rounded border border-line bg-slate-50 px-2 py-1 text-xs text-slate-700"
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <a
                href="#knowledge-review-queue"
                className="inline-flex rounded-md bg-action px-4 py-2 text-sm font-semibold text-white"
              >
                Sprawdź kartę
              </a>
              <button
                type="button"
                className="rounded-md border border-action/30 px-4 py-2 text-sm font-semibold text-action"
                onClick={() => setShowKnowledgeCards((value) => !value)}
              >
                Pokaż kartę
              </button>
            </div>
          </div>
        </article>
        <article className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold text-ink">Co blokuje produkcję treści</h2>
          </div>
          <div className="divide-y divide-line">
            <KnowledgeBlockerRow
              title="Brak zatwierdzenia człowieka"
              description="Karty i propozycje treści wymagają sprawdzenia przed użyciem jako wiedza produkcyjna."
            />
            <KnowledgeBlockerRow
              title="Zablokowane twierdzenia"
              description={
                blockedClaimCount > 0
                  ? `${blockedClaimCount} twierdzeń wymaga blokady albo ręcznego przeglądu.`
                  : "Część twierdzeń może być niepełna, prywatna albo bez jasnego źródła."
              }
            />
            <KnowledgeBlockerRow
              title="Wymagane review"
              description="Publiczne i prywatne źródła Ekologus wymagają oceny człowieka przed użyciem w treściach."
            />
          </div>
          <div className="border-t border-line px-4 py-3">
            <button
              type="button"
              className="text-sm font-semibold text-action"
              onClick={() => setShowKnowledgePlaybooks((value) => !value)}
            >
              Zobacz pełne zasady pracy
            </button>
          </div>
        </article>
      </section>
      <section className="grid gap-4 xl:grid-cols-[1fr_280px]">
        <article id="knowledge-review-queue" className="rounded-md border border-line bg-white">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold text-ink">Kolejka review materiałów źródłowych</h2>
            <button
              type="button"
              className="text-sm font-semibold text-action"
              onClick={() => setShowAllSourceMaterials((value) => !value)}
            >
              {showAllSourceMaterials
                ? "Pokaż krótszą kolejkę"
                : `Pokaż pełną kolejkę (${sourceMaterials.length})`}
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-semibold">Typ</th>
                  <th className="px-4 py-3 font-semibold">Materiał</th>
                  <th className="px-4 py-3 font-semibold">Źródło</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Następny krok</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {knowledgeReviewRows(
                  sourceMaterials,
                  showAllSourceMaterials ? sourceMaterials.length : 8
                ).map((row) => (
                  <tr key={row.id}>
                    <td className="px-4 py-3 font-medium text-action">{row.type}</td>
                    <td className="px-4 py-3 text-slate-700">{row.title}</td>
                    <td className="px-4 py-3 text-slate-600">{row.source}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded px-2 py-1 text-xs font-semibold ${row.statusClass}`}>
                        {row.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{row.nextStep}</td>
                  </tr>
                ))}
                {sourceMaterials.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-5 text-sm text-slate-600">
                      Brak manifestu materiałów źródłowych. Nie zastępujemy go kartami operacyjnymi.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </article>
        <article className="rounded-md border border-line bg-white p-4">
          <h2 className="text-base font-semibold text-ink">Status twierdzeń</h2>
          <div className="mt-4 grid gap-4">
            <ClaimStatusBar
              label="Dozwolone"
              value={allowedClaimCount}
              total={totalClaims}
              className="bg-success"
            />
            <ClaimStatusBar
              label="Wymaga review"
              value={reviewClaimCount}
              total={totalClaims}
              className="bg-wait"
            />
            <ClaimStatusBar
              label="Zakazane"
              value={blockedClaimCount}
              total={totalClaims}
              className="bg-risk"
            />
            <div className="border-t border-line pt-3 text-sm font-semibold text-ink">
              Łącznie {totalClaims}
            </div>
          </div>
        </article>
      </section>
      <section className="rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-ink">Brak osobnego etapu przygotowania.</h2>
            <p className="mt-1 text-sm leading-6 text-slate-700">
              Fakty trafiają do wiedzy produkcyjnej dopiero po decyzji człowieka.
              Każda decyzja jest rejestrowana i możliwa do sprawdzenia.
            </p>
          </div>
          <button
            type="button"
            className="rounded-md border border-action/30 px-4 py-2 text-sm font-semibold text-action"
            onClick={() => setShowKnowledgePlaybooks((value) => !value)}
          >
            Zasady pracy z wiedzą
          </button>
        </div>
      </section>
      {knowledgeMap.isLoading || knowledgeCards.isLoading || playbooks.isLoading ? (
        <section>
          <LoadingBand />
        </section>
      ) : null}
      {knowledgeMap.error || knowledgeCards.error || playbooks.error ? (
        <InlineErrorState message="Nie udało się pobrać pełnej wiedzy. Nie traktuj tego widoku jako gotowego do review." />
      ) : null}
      {showKnowledgeMap ? (
        <section>
          <SectionHeading title="Pełna mapa wiedzy" />
          <KnowledgeMapDetails mapQuery={knowledgeMap} />
        </section>
      ) : null}
      {showKnowledgeCards ? (
        <section>
          <SectionHeading title="Karty wiedzy" />
          <KnowledgeCardsDetails cardsQuery={knowledgeCards} />
        </section>
      ) : null}
      {showKnowledgePlaybooks ? (
        <section>
          <SectionHeading title="Zasady pracy" />
          <KnowledgePlaybooksDetails playbooksQuery={playbooks} />
        </section>
      ) : null}
    </>
  );
}

export function approvedKnowledgeFactCount(
  facts: Array<Pick<KnowledgeSourceFactView, "generation_status">> | undefined
): number {
  return facts?.filter((fact) => fact.generation_status === "eligible").length ?? 0;
}

function KnowledgeStatTile({
  value,
  label,
  cta,
  tone = "default"
}: {
  value: number;
  label: string;
  cta: string;
  tone?: "default" | "success" | "wait" | "action";
}) {
  const toneClass =
    tone === "success"
      ? "bg-success/10 text-success"
      : tone === "wait"
        ? "bg-wait/10 text-wait"
        : tone === "action"
          ? "bg-action/10 text-action"
          : "bg-action/10 text-action";
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex items-center gap-4">
        <div className={`flex h-11 w-11 items-center justify-center rounded-full ${toneClass}`}>
          <ShieldCheck size={20} aria-hidden="true" />
        </div>
        <div>
          <div className="text-2xl font-semibold text-ink">{value}</div>
          <div className="text-sm text-slate-700">{label}</div>
        </div>
      </div>
      <div className="mt-4 text-sm font-semibold text-action">{cta}</div>
    </article>
  );
}

function KnowledgeBlockerRow({ title, description }: { title: string; description: string }) {
  return (
    <div className="px-4 py-3">
      <div className="font-semibold text-ink">{title}</div>
      <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
    </div>
  );
}

type KnowledgeReviewRow = {
  id: string;
  type: string;
  title: string;
  source: string;
  status: string;
  statusClass: string;
  nextStep: string;
};

function knowledgeReviewRows(
  materials: KnowledgeSourceMaterialView[],
  limit = 8
): KnowledgeReviewRow[] {
  return materials.slice(0, limit).map((material) => {
    const imported = material.import_status === "imported";
    return {
      id: `material-${material.source_id}`,
      type: "Materiał źródłowy",
      title: material.title || material.file_name || "Materiał bez tytułu",
      source: material.file_name || material.title || "plik bez nazwy",
      status: imported ? "Zaimportowany" : "Wymaga review excerptu",
      statusClass: imported ? "bg-success/10 text-success" : "bg-wait/10 text-wait",
      nextStep: imported
        ? "Używaj wyłącznie zatwierdzonych faktów z lineage"
        : "Zredaguj i zatwierdź fragment z lineage"
    };
  });
}

function ClaimStatusBar({
  label,
  value,
  total,
  className
}: {
  label: string;
  value: number;
  total: number;
  className: string;
}) {
  const percentage = Math.round((value / total) * 100);
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-ink">{label}</span>
        <span className="font-semibold text-ink">
          {value} <span className="text-xs font-normal text-slate-500">{percentage}%</span>
        </span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${className}`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

function KnowledgeMapDetails({
  mapQuery
}: {
  mapQuery: UseQueryResult<KnowledgeOperatingMapResponse>;
}) {
  if (mapQuery.isLoading) return <LoadingBand />;
  if (mapQuery.error) {
    return <InlineErrorState message="Nie udało się pobrać pełnej mapy wiedzy." />;
  }
  if (!mapQuery.data) {
    return <InlineErrorState message="Mapa wiedzy nie zwróciła danych do pokazania." />;
  }
  return <KnowledgeOperatingMapPanel map={mapQuery.data} />;
}

function KnowledgeCardsDetails({
  cardsQuery
}: {
  cardsQuery: UseQueryResult<KnowledgeCard[]>;
}) {
  if (cardsQuery.isLoading) return <LoadingBand />;
  if (cardsQuery.error) {
    return <InlineErrorState message="Nie udało się pobrać kart wiedzy." />;
  }
  return <KnowledgeCardList cards={cardsQuery.data ?? []} />;
}

function KnowledgePlaybooksDetails({
  playbooksQuery
}: {
  playbooksQuery: UseQueryResult<MarketingPlaybook[]>;
}) {
  if (playbooksQuery.isLoading) return <LoadingBand />;
  if (playbooksQuery.error) {
    return <InlineErrorState message="Nie udało się pobrać playbooków wiedzy." />;
  }
  return <PlaybookList playbooks={playbooksQuery.data ?? []} />;
}
