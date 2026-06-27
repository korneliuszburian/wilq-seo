export function contentMetricFactLabel(metricName: string) {
  const labels: Record<string, string> = {
    ahrefs_content_gap_count: "Luki Ahrefs",
    ahrefs_organic_keyword_gap_count: "Luki fraz z Ahrefs",
    ahrefs_top_page_gap_count: "Mocne strony konkurencji",
    average_position: "Pozycja",
    clicks: "Kliknięcia",
    content_object_count: "Obiekty WP",
    ctr: "CTR",
    impressions: "Wyświetlenia",
    pages_total: "Strony WP",
    posts_total: "Wpisy WP"
  };
  return labels[metricName] ?? metricName;
}

export function formatContentMetricValue(
  metricName: string,
  value: string | number | boolean | null
) {
  if (typeof value === "boolean") return value ? "tak" : "nie";
  if (value === null) return "brak";
  const numericValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numericValue)) return value;
  if (metricName === "ctr" || metricName === "engagement_rate") {
    return `${formatNumber(numericValue * 100, 2)}%`;
  }
  if (metricName === "average_position") {
    return formatNumber(numericValue, 2);
  }
  if (Number.isInteger(numericValue)) return numericValue.toLocaleString("pl-PL");
  return formatNumber(numericValue, 2);
}

export function contentBriefSourceLabel(value: string) {
  const labels: Record<string, string> = {
    gsc_query_page: "Google Search Console",
    ahrefs_gap_review: "Ahrefs do sprawdzenia"
  };
  return labels[value] ?? value;
}

export function contentBriefModeLabel(value: string) {
  const labels: Record<string, string> = {
    refresh: "odświeżenie",
    inventory_check: "sprawdzenie istniejących treści",
    review: "sprawdzenie",
    merge: "scalenie",
    create: "nowa treść",
    block: "blokada"
  };
  return labels[value] ?? value;
}

export function contentDraftOperationLabel(value: string) {
  const labels: Record<string, string> = {
    prepare_existing_content_draft: "wersja robocza istniejącej treści",
    prepare_new_content_draft_review: "wersja robocza nowej treści do sprawdzenia"
  };
  return labels[value] ?? value;
}

export function contentWordPressPostStatusLabel(value?: string | null): string {
  const labels: Record<string, string> = {
    draft: "szkic",
    pending: "czeka na sprawdzenie",
    future: "zaplanowany",
    private: "prywatny",
    publish: "opublikowany"
  };
  return value ? labels[value] ?? value : "brak";
}

export function contentDraftGenerationStatusLabel(value: string) {
  const labels: Record<string, string> = {
    ready_for_review: "gotowy do kontroli",
    blocked_until_content_review: "zablokowany do kontroli treści i URL-a",
    blocked_pending_canonical_duplicate_review: "zablokowany do kontroli URL-i i duplikatów",
    blocked_pending_canonical_duplicate_review_after_url_review:
      "zablokowany do kontroli URL-i i duplikatów",
    blocked_missing_public_inventory: "zablokowany bez spisu publicznych treści"
  };
  return labels[value] ?? value;
}

export function contentPublicationReadinessLabel(value: string) {
  const labels: Record<string, string> = {
    blocked_until_review: "zablokowane do sprawdzenia"
  };
  return labels[value] ?? value;
}

export function contentNextGateLabel(value: string) {
  const labels: Record<string, string> = {
    content_url_preflight_review: "następnie: potwierdź publiczny URL",
    final_canonical_review: "następnie: sprawdź URL kanoniczny",
    duplicate_or_cannibalization_check: "następnie: sprawdź duplikaty"
  };
  return labels[value] ?? `następnie: ${value}`;
}

export function contentPostPublicationMeasurementStatusLabel(value: string): string {
  const labels: Record<string, string> = {
    blocked_until_publish_and_followup_data:
      "zablokowany do publikacji i danych po publikacji"
  };
  return labels[value] ?? value;
}

export function contentWordPressDraftHandoffStatusLabel(value: string): string {
  const labels: Record<string, string> = {
    blocked_until_draft_gates_pass: "zablokowany do przejścia kontroli szkicu",
    blocked_until_draft_readiness_review: "zablokowany do sprawdzenia gotowości szkicu",
    blocked_until_wordpress_draft_handoff_action: "zablokowany do osobnego kroku WordPress"
  };
  return labels[value] ?? value;
}

export function contentDraftOutputKindLabel(value: string): string {
  const labels: Record<string, string> = {
    outline_only_until_gates_pass: "plan treści do czasu kontroli",
    reviewable_polish_draft_preview: "polska wersja robocza do kontroli"
  };
  return labels[value] ?? value;
}

export function contentContractValueLabel(value: string): string {
  const labels: Record<string, string> = {
    api_mutation_ready_false: "zapis zmian nie jest gotowy",
    approve_outline_for_editorial_review: "zatwierdź plan do redakcji",
    automatic_wordpress_write: "automatyczny zapis WordPress",
    blocked_preview_only: "zablokowane do czasu kontroli",
    canonical_review: "kontrola URL-a kanonicznego",
    canonical_needs_target_confirmation: "trzeba potwierdzić URL kanoniczny",
    canonical_review_outcome: "wynik kontroli URL-a kanonicznego",
    candidate_id: "ID wybranej propozycji",
    content_draft_readiness_review: "kontrola gotowości szkicu",
    content_draft_readiness_review_v1: "kontrola gotowości szkicu",
    content_draft_generation_v1: "generowanie szkicu",
    content_url_preflight_review: "potwierdzenie publicznego URL-a",
    content_url_preflight_review_v1: "potwierdzenie publicznego URL-a",
    duplicate_free_claim_without_review: "obietnica braku duplikacji bez kontroli",
    duplicate_or_cannibalization_check: "kontrola duplikacji i kanibalizacji",
    duplicate_review_outcome: "wynik kontroli duplikacji",
    evidence_ids_present: "dowody są podpięte",
    final_canonical_review: "kontrola URL-a kanonicznego",
    legal_factual_review: "kontrola prawna i faktograficzna",
    legal_factual_review_outcome: "wynik kontroli prawnej i faktograficznej",
    human_confirm_before_wordpress_write: "potwierdzenie człowieka przed zapisem WordPress",
    operator_review_approved_for_prepare: "operator zatwierdził przygotowanie",
    merge_required_before_draft: "najpierw trzeba rozstrzygnąć scalenie",
    needs_canonical_fix: "trzeba poprawić kanoniczny URL",
    needs_duplicate_resolution: "trzeba rozstrzygnąć duplikację",
    needs_expert_review: "wymaga kontroli eksperta",
    outline_only_until_gates_pass: "plan treści do czasu kontroli",
    prepare_only_review_recorded: "zapisano ocenę przygotowania",
    publish_ready_claim: "obietnica gotowości do publikacji",
    production_wordpress_write: "zapis na produkcyjnym WordPressie",
    ready_for_review: "gotowe do sprawdzenia",
    ranking_guarantee: "gwarancja pozycji",
    review_only: "do kontroli",
    wordpress_publish: "publikacja WordPress",
    wordpress_draft_handoff_v1: "zapis szkicu WordPress",
    wordpress_draft_handoff_preview_v1: "podgląd szkicu WordPress",
    wordpress_draft_payload_preview: "podgląd wpisu WordPress",
    wordpress_draft_payload_preview_required: "wymagany podgląd wpisu WordPress",
    wordpress_draft_write: "zapis szkicu WordPress",
    wordpress_draft_write_not_requested: "zapis WordPress nie został zlecony",
    wordpress_write_not_requested: "zapis WordPress nie został zlecony",
    gsc_query_page_check: "sprawdzenie zapytań i URL-i z GSC",
    wordpress_existing_url_confirmed: "istniejący URL potwierdzony w WordPress",
    source_connectors_present: "źródła danych są podpięte",
    "28d_before_publish": "28 dni przed publikacją",
    "7d_after_publish": "7 dni po publikacji",
    "28d_after_publish": "28 dni po publikacji",
    "90d_after_publish": "90 dni po publikacji",
    google_search_console: "Google Search Console",
    google_analytics_4: "GA4",
    wordpress_ekologus: "WordPress Ekologus",
    ranking_gain_claim: "obietnica wzrostu pozycji",
    lead_uplift_claim: "obietnica wzrostu leadów",
    revenue_impact_claim: "obietnica wpływu na przychód"
  };
  return labels[value] ?? value;
}

export function contentGateStatusLabel(value: string) {
  const labels: Record<string, string> = {
    confirmed_current_inventory: "potwierdzone na obecnej stronie",
    missing_inventory_match: "brak potwierdzenia w spisie treści",
    current_url_confirmed: "obecny URL potwierdzony",
    needs_final_canonical_review: "sprawdź URL kanoniczny",
    blocked_until_content_url_review: "blokada do kontroli URL",
    blocked_until_inventory_review: "blokada do kontroli spisu treści",
    refresh_or_merge_required: "odśwież albo scal zamiast pisać od nowa",
    manual_merge_or_create_review: "ręcznie wybierz scalenie albo nową treść",
    create_blocked_until_duplicate_check: "nowa treść zablokowana do kontroli",
    not_applicable: "nie dotyczy"
  };
  return labels[value] ?? value;
}

export function contentDecisionTypeLabel(decisionType: string) {
  if (decisionType === "block_until_vendor_read") return "blokada do czasu odczytu";
  if (decisionType === "refresh_or_merge") return "odświeżenie albo scalenie";
  if (decisionType === "merge_create_after_inventory_check") {
    return "scalenie lub utworzenie po kontroli spisu";
  }
  if (decisionType === "inventory_check_before_create") return "kontrola spisu przed briefem";
  if (decisionType === "review_ahrefs_gap_records") return "sprawdzenie luk Ahrefs";
  return "blokada zadania contentowego";
}

export function contentAhrefsGapTypeLabel(value: string) {
  const labels: Record<string, string> = {
    content_gap: "luka treści",
    organic_keyword_gap: "luka fraz",
    top_page_gap: "mocna strona konkurencji",
    backlink_gap: "luka linków",
    competitor_page: "strona konkurencji"
  };
  return labels[value] ?? value;
}

export function contentAhrefsRelevanceLabel(value: string) {
  const labels: Record<string, string> = {
    relevant: "pasuje",
    review: "do sprawdzenia",
    off_topic: "poza tematem"
  };
  return labels[value] ?? value;
}

export function contentAhrefsReasonLabel(value: string) {
  const labels: Record<string, string> = {
    ekologus_domain_term: "pasuje do zakresu Ekologus",
    relevant_competitor_domain: "istotny konkurent",
    gsc_overlap: "pokrywa się z GSC",
    wordpress_inventory_overlap: "pokrywa się z WordPress",
    content_candidate: "propozycja treści",
    backlink_review_only: "sprawdzenie linków",
    off_topic_phrase: "fraza poza tematem",
    off_topic_competitor_domain: "konkurent poza tematem",
    broad_backlink_domain: "szeroki backlink"
  };
  return labels[value] ?? value;
}

export function contentSectionLabel(sectionId: string) {
  if (sectionId === "content_query_page_matrix") return "Zapytania i URL-e z GSC";
  if (sectionId === "content_inventory_match") return "Dopasowanie WordPress";
  if (sectionId === "content_action_safety") return "Bezpieczeństwo akcji";
  return sectionId;
}

export function contentConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje dostępu";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

export function contentRefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  if (status === "running") return "w toku";
  return status;
}

export function wordpressMatchLabel(value: string) {
  if (value === "found") return "potwierdzony";
  if (value === "missing") return "brak potwierdzenia";
  return value;
}

export function wordpressMatchConfidenceLabel(value: string) {
  if (value === "exact_url") return "dokładny URL";
  if (value === "host_alias_sitemap") return "alias hosta z sitemap";
  if (value === "path_fallback") return "dopasowanie ścieżki";
  if (value === "missing") return "brak dopasowania";
  return value;
}

export function contentBlockedClaimLabels(claims: string[]) {
  const labels: Record<string, string> = {
    "conversion uplift": "wzrost konwersji",
    "lead quality": "jakość leadów",
    "ranking win": "wygrana pozycji",
    ROAS: "ROAS",
  };
  return uniqueValues(claims.map((claim) => labels[claim] ?? claim));
}

function formatNumber(value: number, fractionDigits: number) {
  return value.toLocaleString("pl-PL", {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: 0
  });
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)));
}
