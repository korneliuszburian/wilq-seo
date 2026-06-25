export function contentMetricFactLabel(metricName: string) {
  const labels: Record<string, string> = {
    ahrefs_content_gap_count: "Luki Ahrefs",
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

export function contentDraftGenerationStatusLabel(value: string) {
  const labels: Record<string, string> = {
    ready_for_review: "gotowy tylko do sprawdzenia",
    blocked_pending_target_mapping: "zablokowany do potwierdzenia miejsca w projekcie",
    blocked_pending_canonical_duplicate_review: "zablokowany do kontroli URL-i i duplikatów",
    blocked_missing_target_inventory: "zablokowany bez spisu treści z podglądu projektu",
    blocked_until_content_review: "zablokowany do sprawdzenia treści"
  };
  return labels[value] ?? value;
}

export function contentPublicationReadinessLabel(value: string) {
  const labels: Record<string, string> = {
    blocked_until_review: "zablokowane do sprawdzenia"
  };
  return labels[value] ?? value;
}

export function contentTargetSiteStatusLabel(value: string) {
  const labels: Record<string, string> = {
    current_site_match: "bieżąca strona",
    target_site_alias_match: "dopasowanie w podglądzie projektu",
    needs_inventory_match: "wymaga sprawdzenia spisu treści"
  };
  return labels[value] ?? value;
}

export function contentTargetSiteMigrationStatusLabel(value: string) {
  const labels: Record<string, string> = {
    confirmed_target_inventory: "miejsce w projekcie potwierdzone",
    needs_review: "wymaga mapowania",
    blocked_missing_inventory: "brak potwierdzenia w spisie treści",
    not_applicable: "nie dotyczy"
  };
  return labels[value] ?? value;
}

export function candidateInventoryStatusLabel(value: string) {
  const labels: Record<string, string> = {
    confirmed_target_inventory: "kandydat potwierdzony w spisie",
    missing_target_inventory: "kandydat niepotwierdzony",
    not_applicable: "brak kandydata"
  };
  return labels[value] ?? value;
}

export function mappingReviewStatusLabel(value: string) {
  const labels: Record<string, string> = {
    confirm_exact_candidate: "potwierdź wskazany adres",
    review_alternative_candidates: "przejrzyj alternatywy",
    manual_mapping_required: "wymagane ręczne mapowanie",
    not_applicable: "nie dotyczy"
  };
  return labels[value] ?? value;
}

export function contentNextGateLabel(value: string) {
  const labels: Record<string, string> = {
    target_site_mapping_review: "następnie: potwierdź miejsce w projekcie",
    target_site_canonical_review: "następnie: sprawdź URL kanoniczny",
    duplicate_or_cannibalization_check: "następnie: sprawdź duplikaty"
  };
  return labels[value] ?? `następnie: ${value}`;
}

export function contentTargetSiteMappingStatusLabel(status?: string | null) {
  if (status === "target_site_inventory_confirmed") {
    return "spis treści w podglądzie potwierdzony";
  }
  if (status === "target_site_mapping_review_needed") {
    return "wymaga mapowania";
  }
  if (status === "current_site_inventory_confirmed") {
    return "potwierdzono obecną stronę";
  }
  return "brak mapowania miejsca w projekcie";
}

export function contentPostPublicationMeasurementStatusLabel(value: string): string {
  const labels: Record<string, string> = {
    blocked_until_publish_and_followup_data:
      "zablokowany do publikacji i danych po publikacji"
  };
  return labels[value] ?? value;
}

export function contentStagingHandoffStatusLabel(value: string): string {
  const labels: Record<string, string> = {
    blocked_until_draft_gates_pass: "zablokowany do przejścia kontroli szkicu",
    blocked_until_draft_readiness_review: "zablokowany do sprawdzenia gotowości szkicu",
    blocked_until_staging_action_contract: "zablokowany do osobnego kroku WordPress"
  };
  return labels[value] ?? value;
}

export function contentDraftOutputKindLabel(value: string): string {
  const labels: Record<string, string> = {
    outline_only_until_gates_pass: "tylko plan treści do czasu kontroli",
    reviewable_polish_draft_preview: "polska wersja robocza tylko do sprawdzenia"
  };
  return labels[value] ?? value;
}

export function contentGateStatusLabel(value: string) {
  const labels: Record<string, string> = {
    confirmed_current_inventory: "potwierdzone na obecnej stronie",
    confirmed_target_inventory: "potwierdzone w podglądzie projektu",
    missing_inventory_match: "brak potwierdzenia w spisie treści",
    current_url_confirmed: "obecny URL potwierdzony",
    needs_target_canonical_review: "sprawdź URL kanoniczny",
    blocked_until_mapping_review: "blokada do mapowania URL",
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
    content_candidate: "kandydat contentowy",
    backlink_review_only: "tylko sprawdzenie linków",
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
  if (status === "missing_credentials") return "brakuje credentiali";
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
    "auto publish": "automatyczna publikacja",
    "content rewrite": "rewrite treści bez dowodu",
    "conversion uplift": "wzrost konwersji",
    "duplicate avoidance": "uniknięcie duplikacji",
    "duplicate-free guarantee": "gwarancja braku duplikatów",
    "lead uplift": "wzrost leadów",
    "merge plan": "plan scalenia",
    "new article without inventory check": "nowy artykuł bez kontroli spisu treści",
    "ranking guarantee": "gwarancja pozycji",
    "ranking win": "wygrana pozycji",
    "refresh plan": "plan odświeżenia",
    "revenue impact": "wpływ na przychód",
    ROAS: "ROAS",
    "wordpress write": "zapis do WordPress"
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
