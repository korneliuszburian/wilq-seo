import type {
  ContentWorkItemQualityReviewResponse,
  ContentWorkItemRevisionPlanResponse,
  ContentWorkItemStructuredDraftPreviewResponse,
  ContentWorkItemStructuredDraftRuntimeResponse,
  ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
  ContentWorkItemWordPressDraftExecutionResponse
} from "../lib/api";
import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";
import { wordpressDraftExecutionStatusText } from "./WordPressDraftStatus";

export function draftSafetyText(publishReady?: boolean) {
  if (publishReady) return "Szkic wymaga zatrzymania, bo został oznaczony jako gotowy do publikacji.";
  return "Szkic jest paczką do review, nie tekstem do automatycznej publikacji.";
}

export function handoffSafetyText(publishAllowed?: boolean) {
  if (publishAllowed === undefined) {
    return "WordPress nie dostaje jeszcze szkicu. Najpierw człowiek musi zatwierdzić brief, ryzykowne twierdzenia i paczkę szkicu, a WILQ musi zapisać audyt.";
  }
  if (publishAllowed) {
    return "Publikacja wymaga osobnej blokady, bo WILQ nie powinien publikować automatycznie.";
  }
  return "Handoff przygotowuje tylko szkic. Publikacja i nadpisanie treści są zablokowane.";
}

export function structuredRuntimeSafetyText(
  result: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
) {
  if (!result) {
    return "WILQ może sprawdzić przygotowanie szkicu bez pisania na żywo. Ten krok nie wywołuje modelu.";
  }
  if (result.status === "generated" && result.output) {
    return "Szkic został wygenerowany w kontrolowanym trybie. Przed WordPress musi przejść podgląd treści i sprawdzenie człowieka.";
  }
  if (result.external_call_attempted) {
    return "Zatrzymaj workflow: próba przygotowania szkicu nie powinna wywoływać modelu na żywo.";
  }
  if (result.status === "blocked") {
    return result.blockers[0]?.reason ?? "WILQ zablokował przygotowanie próby szkicu.";
  }
  return "Próba gotowa: WILQ ma kontrakt szkicu i nie wygenerował treści na żywo.";
}

export function structuredPreviewSafetyText(
  result: ContentWorkItemStructuredDraftPreviewResponse["preview_result"] | null
) {
  if (!result) {
    return "Po wygenerowaniu szkicu WILQ pokaże treść do sprawdzenia. To nadal nie jest publikacja.";
  }
  if (result.blockers.length) {
    return result.blockers[0]?.reason ?? "WILQ zablokował podgląd treści.";
  }
  if (result.preview) {
    return "Podgląd gotowy do sprawdzenia przez człowieka. WordPress i publikacja nadal są zablokowane.";
  }
  return "WILQ nie zwrócił treści do podglądu.";
}

export function qualityReviewSafetyText(
  review: ContentWorkItemQualityReviewResponse["quality_review"] | null
) {
  if (!review) {
    return (
      "Po podglądzie treści WILQ sprawdzi dowody, ryzykowne obietnice, CTA, " +
      "dopasowanie do usługi i gotowość pomiaru. To nie jest wynik SEO."
    );
  }
  if (review.blockers.length) {
    return review.blockers[0]?.reason ?? "WILQ blokuje szkic przed sprawdzeniem człowieka.";
  }
  if (review.revision_instructions.length) {
    return "Szkic wymaga ograniczonej poprawki przed sprawdzeniem człowieka.";
  }
  return "Szkic może trafić do sprawdzenia człowieka. Nadal nie jest publikacją.";
}

export function revisionPlanSafetyText(
  plan: ContentWorkItemRevisionPlanResponse["revision_plan"] | null
) {
  if (!plan) {
    return "Plan poprawki może powstać tylko z oceny jakości WILQ. Nie regenerujemy szkicu wolnym promptem.";
  }
  if (plan.blockers.length) {
    return plan.blockers[0]?.reason ?? "WILQ blokuje plan poprawki.";
  }
  if (plan.instructions.length) {
    return "Poprawka jest ograniczona do wskazanych zmian i dowodów. Po poprawce trzeba ponownie uruchomić ocenę jakości.";
  }
  return "Ocena jakości nie wymaga poprawki. Następny krok to sprawdzenie człowieka.";
}

export function wordpressExecutionSafetyText(
  result: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] | null
) {
  if (!result) {
    return "Po audycie WILQ może pokazać, co trafiłoby do WordPress. Ten krok nie wykonuje zewnętrznego zapisu.";
  }
  if (result.status === "created") {
    return wordpressDraftExecutionStatusText(result);
  }
  if (result.external_write_attempted) {
    return "Zatrzymaj workflow: WordPress zgłosił próbę zapisu bez potwierdzonego utworzenia szkicu.";
  }
  if (result.status === "blocked") {
    return result.blockers[0]?.reason ?? "WILQ zablokował przygotowanie podglądu szkicu.";
  }
  if (result.payload) {
    return `Podgląd gotowy: WordPress dostałby status ${result.payload.post_status}. Publikacja: zablokowana. Nadpisywanie treści: zablokowane.`;
  }
  return "WILQ sprawdził przekazanie, ale nie zwrócił paczki podglądu.";
}

export function acfPreviewSafetyText(
  result: ContentWorkItemWordPressAuthoringPayloadPreviewResponse["preview_result"] | null
) {
  if (!result) {
    return "Po audycie WILQ może pokazać, który layout ACF i które pola szkicu wypełni. Ten krok nie wykonuje zapisu w WordPress.";
  }
  if (result.external_write_attempted) {
    return "Zatrzymaj workflow: mapowanie ACF nie powinno wykonywać zewnętrznego zapisu.";
  }
  if (result.blockers.length) {
    return result.blockers[0]?.reason ?? "WILQ zablokował mapowanie ACF.";
  }
  const firstSection = result.sections[0] ?? null;
  const fieldCount = firstSection
    ? Object.values(firstSection.field_values).filter((value) => Boolean(value)).length
    : 0;
  if (firstSection) {
    return `Mapowanie gotowe: WILQ użyje layoutu ${firstSection.layout_label} i wypełni ${fieldCount} pól. Publikacja i nadpisywanie pozostają zablokowane.`;
  }
  return "Mapowanie ACF jest gotowe, ale WILQ nie zwrócił sekcji do pokazania.";
}

export function measurementSafetyText(
  window: ContentWorkflowSnapshot["measurementWindow"]["measurement_window_result"]["window"]
) {
  if (!window) return "Brak okna pomiaru blokuje jakiekolwiek wnioski o efekcie treści.";
  return `Pierwsza ocena po ${window.earliest_verdict_date}. Do tego czasu WILQ zbiera dane, ale nie claimuje sukcesu ani porażki.`;
}

export function reviewControlDisabledReason(
  data: ContentWorkflowSnapshot,
  hasDraft: boolean,
  pending: boolean
) {
  if (pending) return "WILQ zapisuje sprawdzenie.";
  if (data.humanReview.review) return "Sprawdzenie człowieka jest już zapisane dla tego tematu.";
  if (!hasDraft) return "Najpierw WILQ musi przygotować paczkę szkicu do sprawdzenia.";
  if (!data.preflight.item.evidence_ids.length) {
    return "Sprawdzenie nie może ruszyć bez dowodów przypiętych do tematu.";
  }
  return null;
}

export function auditControlDisabledReason(data: ContentWorkflowSnapshot, pending: boolean) {
  if (pending) return "WILQ zapisuje audyt przekazania szkicu.";
  if (data.wordpressHandoff.handoff_result.handoff) {
    return "Audyt jest zapisany, a przekazanie do WordPress pozostaje przygotowane tylko jako szkic.";
  }
  if (!data.humanReview.review) return "Najpierw zapisz sprawdzenie człowieka.";
  if (!data.humanReview.wordpress_handoff_allowed) {
    return (
      data.humanReview.blockers[0]?.reason ??
      "WILQ nie odblokował przekazania do WordPress po sprawdzeniu."
    );
  }
  return null;
}

export function structuredRuntimeControlDisabledReason(
  data: ContentWorkflowSnapshot,
  pending: boolean,
  result: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
) {
  if (pending) return "WILQ sprawdza gotowość szkicu.";
  if (result) return "Próba przygotowania szkicu jest już sprawdzona dla tej sesji.";
  if (!data.structuredGeneration.structured_generation_result.contract) {
    return (
      data.structuredGeneration.structured_generation_result.blockers[0]?.reason ??
      "Najpierw WILQ musi przygotować kontrakt szkicu."
    );
  }
  return null;
}

export function structuredPreviewControlDisabledReason(
  data: ContentWorkflowSnapshot,
  pending: boolean,
  result: ContentWorkItemStructuredDraftPreviewResponse["preview_result"] | null,
  runtimeResult: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
) {
  if (pending) return "WILQ sprawdza podgląd treści.";
  if (result) return "Podgląd treści jest już przygotowany dla tej sesji.";
  if (!data.structuredGeneration.structured_generation_result.contract) {
    return (
      data.structuredGeneration.structured_generation_result.blockers[0]?.reason ??
      "Najpierw WILQ musi przygotować kontrakt szkicu."
    );
  }
  if (!runtimeResult?.output) {
    return "Najpierw WILQ musi mieć wygenerowany szkic. Sama próba gotowości nie tworzy treści.";
  }
  return null;
}

export function qualityReviewControlDisabledReason(
  pending: boolean,
  review: ContentWorkItemQualityReviewResponse["quality_review"] | null,
  runtimeResult: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"] | null
) {
  if (pending) return "WILQ sprawdza jakość szkicu.";
  if (review) return "Ocena jakości jest już przygotowana dla tej sesji.";
  if (!runtimeResult?.output) {
    return "Najpierw WILQ musi mieć wygenerowany szkic do oceny jakości.";
  }
  return null;
}

export function revisionPlanControlDisabledReason(
  pending: boolean,
  plan: ContentWorkItemRevisionPlanResponse["revision_plan"] | null,
  review: ContentWorkItemQualityReviewResponse["quality_review"] | null
) {
  if (pending) return "WILQ przygotowuje plan poprawki.";
  if (plan) return "Plan poprawki jest już przygotowany dla tej sesji.";
  if (!review) return "Najpierw uruchom ocenę jakości szkicu.";
  return null;
}

export function acfPreviewControlDisabledReason(
  hasDraft: boolean,
  hasHandoff: boolean,
  hasAuthoringProfile: boolean,
  pending: boolean,
  result: ContentWorkItemWordPressAuthoringPayloadPreviewResponse["preview_result"] | null
) {
  if (pending) return "WILQ sprawdza mapowanie ACF.";
  if (result) return "Mapowanie ACF jest już przygotowane dla tej sesji.";
  if (!hasAuthoringProfile) return "Najpierw WILQ musi odczytać profil WordPress/ACF.";
  if (!hasDraft) return "Najpierw WILQ musi przygotować paczkę szkicu.";
  if (!hasHandoff) return "Najpierw zapisz audyt i przygotuj przekazanie szkicu do WordPress.";
  return null;
}

export function executionControlDisabledReason(
  hasDraft: boolean,
  hasHandoff: boolean,
  pending: boolean,
  result: ContentWorkItemWordPressDraftExecutionResponse["execution_result"] | null
) {
  if (pending) return "WILQ przygotowuje podgląd szkicu WordPress.";
  if (result) return "Podgląd szkicu WordPress jest już przygotowany dla tej sesji.";
  if (!hasDraft) return "Najpierw WILQ musi przygotować paczkę szkicu.";
  if (!hasHandoff) return "Najpierw zapisz audyt i przygotuj przekazanie szkicu do WordPress.";
  return null;
}
