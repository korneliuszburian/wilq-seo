import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ActionObject } from "../lib/api";
import * as actionApi from "../lib/api";
import { ResearchPacketV3ActionReview } from "./ResearchPacketV3ActionReview";

const digest = (character: string) => character.repeat(64);

function actionWithPacket({
  exactPageIdentity = true,
  pageUrl,
  canonicalPath,
  perUrlIdentityActionId = "act_per_url_delivery_identity_exact",
  demandEvidenceStatus = "missing",
  searchIntent = null,
  actionStatus = "ready_to_apply",
  lastReviewOutcome = null,
  lastMutationAuditStatus = null
}: {
  exactPageIdentity?: boolean;
  pageUrl?: string;
  canonicalPath?: string;
  perUrlIdentityActionId?: string | null;
  demandEvidenceStatus?: "available" | "missing";
  searchIntent?: string | null;
  actionStatus?: "ready_to_apply" | "applied";
  lastReviewOutcome?: "approved_for_prepare" | "needs_changes" | "rejected" | "deferred" | null;
  lastMutationAuditStatus?: "blocked" | "applied" | "failed" | null;
} = {}): ActionObject {
  const packet = {
    schema_version: "wilq_research_packet_v3_preview_record_v1",
    preview_hash: digest("a"),
    work_item_id: "wi_exact",
    snapshot: {
      contract_version: "research_packet_v3_preview",
      status: "ready",
      work_item_id: "wi_exact",
      preview_id: "content_research_packet_v3_aaaaaaaaaaaaaaaaaaaaaaaa",
      preview_hash: digest("a"),
      source_pack_id: `source_pack_v3_${digest("b")}`,
      source_pack_hash: digest("b"),
      page_url: exactPageIdentity ? (pageUrl ?? "https://www.ekologus.pl/exact/") : undefined,
      canonical_path: exactPageIdentity ? (canonicalPath ?? "/exact") : undefined,
      per_url_delivery_identity_action_id: perUrlIdentityActionId ?? undefined,
      identity_digest: digest("c"),
      material_meaning_digest: digest("d"),
      planning_input_digest: digest("e"),
      demand_evidence_status: demandEvidenceStatus,
      selected_facts: [{
        source_fact_id: "fact_exact",
        fact_digest: digest("f"),
        text: "Zatwierdzony fakt z oficjalnego źródła.",
        source_reference: "https://eli.gov.pl/acts/synthetic",
        freshness_date: "2026-09-24",
        source_type: "legal_update",
        official_source: true,
        privacy_class: "commit_safe",
        source_connectors: ["official_regulatory_review"],
        evidence_ids: ["ev_official_fact"],
        regulatory_requirement_ids: ["requirement_exact"]
      }],
      planning_context: {
        target_reader: "Przedsiębiorca",
        buyer_problem: "Niejasny obowiązek",
        buyer_trigger: "Zmiana prawa",
        search_intent: searchIntent
      },
      cta_direction: "Kontakt z doradcą",
      minimum_cta_blocks: 1,
      required_cta_patterns: [],
      internal_links: [{
        target_url: "https://www.ekologus.pl/kontakt/",
        anchor_hint: "Kontakt",
        source_connector: "wordpress_ekologus",
        evidence_ids: ["ev_link"]
      }],
      regulatory_profile_id: "profile_exact",
      regulatory_profile_version: "v1",
      legal_requirements: [{
        requirement_id: "requirement_exact",
        label: "Wymaganie prawne",
        source_fact_ids: ["fact_exact"],
        evidence_ids: ["ev_official_fact"]
      }],
      verification_evidence_ids: ["ev_official_fact", "ev_link"],
      verification_evidence_digest: digest("1"),
      blocker: null,
      generation_allowed: false,
      packet_write_allowed: false
    }
  };
  return {
    id: "act_content_research_packet_v3_exact",
    status: actionStatus,
    payload: {
      action_type: "content_research_packet_v3_approval",
      local_authority_only: true,
      legacy_wordpress_claim: "UNREVIEWED OLD PAGE CLAIM",
      stale_gsc_rows: ["STALE GSC QUERY ROW"],
      old_gsc_metrics: ["STALE GSC METRIC"],
      research_packet_v3_preview: packet
    },
    review_gate: {
      apply_allowed: false,
      last_review_outcome: lastReviewOutcome,
      last_mutation_audit_status: lastMutationAuditStatus
    },
    metrics: []
  } as unknown as ActionObject;
}

function renderReview(action = actionWithPacket()) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
      <ResearchPacketV3ActionReview action={action} />
    </QueryClientProvider>
  );
}

function completeRequiredDecisionInputs() {
  fireEvent.change(screen.getByLabelText("Powód decyzji"), {
    target: { value: "Potwierdzam pełny odczyt dokładnego pakietu." }
  });
  fireEvent.click(screen.getByRole("checkbox", { name: /Przeczytałem dokładny pakiet/ }));
}

const lifecycleStages = ["validate", "preview", "review", "confirm", "impact", "apply"] as const;
const lifecycleFailureCases = lifecycleStages.flatMap((stage) => (
  (["blocked", "throws"] as const).map((mode) => ({ stage, mode }))
));

describe("v3 research packet ActionObject review", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows only exact official packet material and runs acceptance through every guarded stage in order", async () => {
    const callOrder: string[] = [];
    vi.spyOn(actionApi, "validateAction").mockImplementation(async () => {
      callOrder.push("validate");
      return { valid: true, status: "valid" } as never;
    });
    vi.spyOn(actionApi, "previewAction").mockImplementation(async () => {
      callOrder.push("preview");
      return { status: "preview_ready", blockers: [] } as never;
    });
    const review = vi.spyOn(actionApi, "reviewAction").mockImplementation(async () => {
      callOrder.push("review");
      return { status: "recorded" } as never;
    });
    vi.spyOn(actionApi, "confirmAction").mockImplementation(async () => {
      callOrder.push("confirm");
      return { confirmed: true, status: "confirmed", blockers: [] } as never;
    });
    vi.spyOn(actionApi, "impactCheckAction").mockImplementation(async () => {
      callOrder.push("impact");
      return { status: "checked", blockers: [] } as never;
    });
    vi.spyOn(actionApi, "applyAction").mockImplementation(async () => {
      callOrder.push("apply");
      return { applied: true, status: "applied" } as never;
    });

    renderReview();

    const accept = screen.getByRole("button", { name: "Akceptuję" });
    const reject = screen.getByRole("button", { name: "Nie akceptuję" });
    expect(accept).toBeDisabled();
    expect(reject).toBeDisabled();
    expect(screen.getByText("https://www.ekologus.pl/exact/")).toBeInTheDocument();
    expect(screen.getByText("Ścieżka kanoniczna: /exact")).toBeInTheDocument();
    expect(screen.getByText("Zatwierdzony fakt z oficjalnego źródła.")).toBeInTheDocument();
    expect(screen.getByRole("link", {
      name: "Otwórz oficjalne źródło: https://eli.gov.pl/acts/synthetic"
    }))
      .toHaveAttribute("href", "https://eli.gov.pl/acts/synthetic");
    expect(screen.getByText(/Aktualność źródła: 2026-09-24/)).toBeInTheDocument();
    expect(screen.getByText(/Brak bieżących danych popytowych/)).toBeInTheDocument();
    expect(screen.queryByText("UNREVIEWED OLD PAGE CLAIM")).not.toBeInTheDocument();
    expect(screen.queryByText("STALE GSC QUERY ROW")).not.toBeInTheDocument();
    expect(screen.queryByText("STALE GSC METRIC")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Zapisz przegląd" })).not.toBeInTheDocument();

    completeRequiredDecisionInputs();
    expect(accept).toBeEnabled();
    fireEvent.click(accept);

    await waitFor(() => expect(callOrder).toEqual([
      "validate", "preview", "review", "confirm", "impact", "apply"
    ]));
    expect(review).toHaveBeenCalledWith("act_content_research_packet_v3_exact", {
      outcome: "approved_for_prepare",
      reviewed_by: "operator_local_dashboard",
      notes: "Potwierdzam pełny odczyt dokładnego pakietu.",
      checked_items: ["reviewed_full_packet"],
      blockers: []
    });
  });

  it("blocks review when a historical packet lacks the current per-URL identity", () => {
    renderReview(actionWithPacket({ perUrlIdentityActionId: null }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      /Brakuje zatwierdzonego per-URL identity/
    );
    expect(screen.getByRole("button", { name: "Akceptuję" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Nie akceptuję" })).toBeDisabled();
  });

  it("records only the rejected review after the same attestation", async () => {
    const review = vi.spyOn(actionApi, "reviewAction").mockResolvedValue({ status: "recorded" } as never);
    const validate = vi.spyOn(actionApi, "validateAction");
    const preview = vi.spyOn(actionApi, "previewAction");
    const confirm = vi.spyOn(actionApi, "confirmAction");
    const impact = vi.spyOn(actionApi, "impactCheckAction");
    const apply = vi.spyOn(actionApi, "applyAction");
    renderReview();

    completeRequiredDecisionInputs();
    fireEvent.click(screen.getByRole("button", { name: "Nie akceptuję" }));

    await waitFor(() => expect(review).toHaveBeenCalledWith("act_content_research_packet_v3_exact", {
      outcome: "rejected",
      reviewed_by: "operator_local_dashboard",
      notes: "Potwierdzam pełny odczyt dokładnego pakietu.",
      checked_items: ["reviewed_full_packet"],
      blockers: []
    }));
    expect(validate).not.toHaveBeenCalled();
    expect(preview).not.toHaveBeenCalled();
    expect(confirm).not.toHaveBeenCalled();
    expect(impact).not.toHaveBeenCalled();
    expect(apply).not.toHaveBeenCalled();
  });

  it("disables both decisions after a prior rejected review in the ActionObject readback", () => {
    const validate = vi.spyOn(actionApi, "validateAction");
    const preview = vi.spyOn(actionApi, "previewAction");
    const review = vi.spyOn(actionApi, "reviewAction");
    const confirm = vi.spyOn(actionApi, "confirmAction");
    const impact = vi.spyOn(actionApi, "impactCheckAction");
    const apply = vi.spyOn(actionApi, "applyAction");

    renderReview(actionWithPacket({ lastReviewOutcome: "rejected" }));
    completeRequiredDecisionInputs();

    expect(screen.getByRole("button", { name: "Akceptuję" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Nie akceptuję" })).toBeDisabled();
    expect(validate).not.toHaveBeenCalled();
    expect(preview).not.toHaveBeenCalled();
    expect(review).not.toHaveBeenCalled();
    expect(confirm).not.toHaveBeenCalled();
    expect(impact).not.toHaveBeenCalled();
    expect(apply).not.toHaveBeenCalled();
  });

  it("disables both decisions after an applied mutation in the ActionObject readback", () => {
    const validate = vi.spyOn(actionApi, "validateAction");
    const preview = vi.spyOn(actionApi, "previewAction");
    const review = vi.spyOn(actionApi, "reviewAction");
    const confirm = vi.spyOn(actionApi, "confirmAction");
    const impact = vi.spyOn(actionApi, "impactCheckAction");
    const apply = vi.spyOn(actionApi, "applyAction");

    renderReview(actionWithPacket({
      actionStatus: "applied",
      lastMutationAuditStatus: "applied"
    }));
    completeRequiredDecisionInputs();

    expect(screen.getByRole("button", { name: "Akceptuję" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Nie akceptuję" })).toBeDisabled();
    expect(validate).not.toHaveBeenCalled();
    expect(preview).not.toHaveBeenCalled();
    expect(review).not.toHaveBeenCalled();
    expect(confirm).not.toHaveBeenCalled();
    expect(impact).not.toHaveBeenCalled();
    expect(apply).not.toHaveBeenCalled();
  });

  it.each([
    { decision: "rejected" as const, button: "Nie akceptuję" },
    { decision: "applied" as const, button: "Akceptuję" }
  ])("disables both decisions after this view records $decision and blocks further calls", async ({
    decision,
    button
  }) => {
    const calls = {
      validate: vi.spyOn(actionApi, "validateAction").mockResolvedValue({
        valid: true,
        status: "valid"
      } as never),
      preview: vi.spyOn(actionApi, "previewAction").mockResolvedValue({
        status: "preview_ready",
        blockers: []
      } as never),
      review: vi.spyOn(actionApi, "reviewAction").mockResolvedValue({
        status: "recorded"
      } as never),
      confirm: vi.spyOn(actionApi, "confirmAction").mockResolvedValue({
        confirmed: true,
        status: "confirmed",
        blockers: []
      } as never),
      impact: vi.spyOn(actionApi, "impactCheckAction").mockResolvedValue({
        status: "checked",
        blockers: []
      } as never),
      apply: vi.spyOn(actionApi, "applyAction").mockResolvedValue({
        applied: true,
        status: "applied"
      } as never)
    };
    renderReview();
    completeRequiredDecisionInputs();

    fireEvent.click(screen.getByRole("button", { name: button }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Akceptuję" })).toBeDisabled());
    expect(screen.getByRole("button", { name: "Nie akceptuję" })).toBeDisabled();

    const callCountsAfterDecision = Object.fromEntries(
      Object.entries(calls).map(([stage, mock]) => [stage, mock.mock.calls.length])
    );
    fireEvent.click(screen.getByRole("button", { name: "Akceptuję" }));
    fireEvent.click(screen.getByRole("button", { name: "Nie akceptuję" }));
    expect(Object.fromEntries(
      Object.entries(calls).map(([stage, mock]) => [stage, mock.mock.calls.length])
    )).toEqual(callCountsAfterDecision);

    if (decision === "rejected") {
      expect(calls.review).toHaveBeenCalledTimes(1);
      expect(calls.validate).not.toHaveBeenCalled();
    } else {
      expect(calls.validate).toHaveBeenCalledTimes(1);
      expect(calls.preview).toHaveBeenCalledTimes(1);
      expect(calls.review).toHaveBeenCalledTimes(1);
      expect(calls.confirm).toHaveBeenCalledTimes(1);
      expect(calls.impact).toHaveBeenCalledTimes(1);
      expect(calls.apply).toHaveBeenCalledTimes(1);
    }
  });

  it("stops acceptance at the first blocked ActionObject stage", async () => {
    const callOrder: string[] = [];
    vi.spyOn(actionApi, "validateAction").mockImplementation(async () => {
      callOrder.push("validate");
      return { valid: true, status: "valid" } as never;
    });
    vi.spyOn(actionApi, "previewAction").mockImplementation(async () => {
      callOrder.push("preview");
      return { status: "blocked", blockers: ["payload_preview_missing"], blocker_labels: [] } as never;
    });
    const review = vi.spyOn(actionApi, "reviewAction");
    const confirm = vi.spyOn(actionApi, "confirmAction");
    const impact = vi.spyOn(actionApi, "impactCheckAction");
    const apply = vi.spyOn(actionApi, "applyAction");
    renderReview();

    completeRequiredDecisionInputs();
    fireEvent.click(screen.getByRole("button", { name: "Akceptuję" }));

    await waitFor(() => expect(callOrder).toEqual(["validate", "preview"]));
    expect(review).not.toHaveBeenCalled();
    expect(confirm).not.toHaveBeenCalled();
    expect(impact).not.toHaveBeenCalled();
    expect(apply).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/Zatrzymano na etapie: podgląd/);
    expect(screen.getByRole("button", { name: "Akceptuję" })).toBeEnabled();
  });

  it("requires a nonblank reason capped at 2000 characters before decisions", () => {
    const validate = vi.spyOn(actionApi, "validateAction");
    const review = vi.spyOn(actionApi, "reviewAction");
    renderReview();

    const reason = screen.getByLabelText("Powód decyzji");
    expect(reason).toHaveValue("");
    expect(reason).toBeRequired();
    expect(reason).toHaveProperty("maxLength", 2000);
    fireEvent.change(reason, { target: { value: "   " } });
    fireEvent.click(screen.getByRole("checkbox", { name: /Przeczytałem dokładny pakiet/ }));
    expect(screen.getByRole("button", { name: "Akceptuję" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Nie akceptuję" })).toBeDisabled();
    expect(validate).not.toHaveBeenCalled();
    expect(review).not.toHaveBeenCalled();
  });

  it.each(lifecycleFailureCases)(
    "stops acceptance when $stage $mode",
    async ({ stage, mode }) => {
      const callOrder: string[] = [];
      const validate = vi.spyOn(actionApi, "validateAction").mockImplementation(async () => {
        callOrder.push("validate");
        return { valid: true, status: "valid" } as never;
      });
      const preview = vi.spyOn(actionApi, "previewAction").mockImplementation(async () => {
        callOrder.push("preview");
        return { status: "preview_ready", blockers: [] } as never;
      });
      const review = vi.spyOn(actionApi, "reviewAction").mockImplementation(async () => {
        callOrder.push("review");
        return { status: "recorded" } as never;
      });
      const confirm = vi.spyOn(actionApi, "confirmAction").mockImplementation(async () => {
        callOrder.push("confirm");
        return { confirmed: true, status: "confirmed", blockers: [] } as never;
      });
      const impact = vi.spyOn(actionApi, "impactCheckAction").mockImplementation(async () => {
        callOrder.push("impact");
        return { status: "checked", blockers: [] } as never;
      });
      const apply = vi.spyOn(actionApi, "applyAction").mockImplementation(async () => {
        callOrder.push("apply");
        return { applied: true, status: "applied" } as never;
      });
      const fail = (name: typeof stage, run: () => void) => {
        if (stage === name) run();
      };
      const throwing = () => {
        throw new Error(`synthetic ${stage} failure`);
      };

      fail("validate", () => validate.mockImplementation(async () => {
        callOrder.push("validate");
        if (mode === "throws") throwing();
        return { valid: false, status: "blocked", errors: ["blocked"] } as never;
      }));
      fail("preview", () => preview.mockImplementation(async () => {
        callOrder.push("preview");
        if (mode === "throws") throwing();
        return { status: "blocked", blockers: ["blocked"], blocker_labels: [] } as never;
      }));
      fail("review", () => review.mockImplementation(async () => {
        callOrder.push("review");
        if (mode === "throws") throwing();
        return { status: "blocked" } as never;
      }));
      fail("confirm", () => confirm.mockImplementation(async () => {
        callOrder.push("confirm");
        if (mode === "throws") throwing();
        return { confirmed: false, status: "blocked", blockers: ["blocked"] } as never;
      }));
      fail("impact", () => impact.mockImplementation(async () => {
        callOrder.push("impact");
        if (mode === "throws") throwing();
        return { status: "blocked", blockers: ["blocked"] } as never;
      }));
      fail("apply", () => apply.mockImplementation(async () => {
        callOrder.push("apply");
        if (mode === "throws") throwing();
        return { applied: false, status: "blocked", errors: ["blocked"] } as never;
      }));

      renderReview();
      completeRequiredDecisionInputs();
      fireEvent.click(screen.getByRole("button", { name: "Akceptuję" }));

      const lastStageIndex = lifecycleStages.indexOf(stage);
      await waitFor(() => expect(callOrder).toEqual(lifecycleStages.slice(0, lastStageIndex + 1)));
      expect(screen.getByRole("alert")).toBeInTheDocument();
    }
  );

  it("renders an exact raw Unicode page identity as reviewable", () => {
    renderReview(actionWithPacket({
      pageUrl: "https://www.ekologus.pl/zażółć/",
      canonicalPath: "/zażółć"
    }));

    expect(screen.getByRole("heading", { name: "Przegląd dokładnego pakietu badawczego" }))
      .toBeInTheDocument();
    expect(screen.getByText("Ścieżka kanoniczna: /zażółć")).toBeInTheDocument();
  });

  it("describes available demand as search intent only without rendering rows or metrics", () => {
    renderReview(actionWithPacket({
      demandEvidenceStatus: "available",
      searchIntent: "Obowiązki dla przedsiębiorcy"
    }));

    expect(screen.getByText("Intencja")).toBeInTheDocument();
    expect(screen.getByText("Obowiązki dla przedsiębiorcy")).toBeInTheDocument();
    expect(screen.getByText(/Pakiet zawiera wyłącznie pokazaną wyżej intencję wyszukiwania/))
      .toBeInTheDocument();
    expect(screen.getByText(/nie udostępnia wierszy ani metryk/)).toBeInTheDocument();
    expect(screen.queryByText("STALE GSC QUERY ROW")).not.toBeInTheDocument();
    expect(screen.queryByText("STALE GSC METRIC")).not.toBeInTheDocument();
    expect(screen.queryByText(/Brak bieżących danych popytowych/)).not.toBeInTheDocument();
  });

  it("fails closed before either decision when the packet lacks exact page identity", () => {
    renderReview(actionWithPacket({ exactPageIdentity: false }));
    expect(screen.getByRole("alert")).toHaveTextContent(/Brakuje dokładnego adresu strony/);
    expect(screen.getByRole("button", { name: "Akceptuję" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Nie akceptuję" })).toBeDisabled();
  });

  it("offers the planning generation intent only after the packet receipt is applied", async () => {
    vi.spyOn(actionApi, "validateAction").mockResolvedValue({ valid: true, status: "valid" } as never);
    vi.spyOn(actionApi, "previewAction").mockResolvedValue({ status: "preview_ready", blockers: [] } as never);
    vi.spyOn(actionApi, "reviewAction").mockResolvedValue({ status: "recorded" } as never);
    vi.spyOn(actionApi, "confirmAction").mockResolvedValue({ confirmed: true, status: "confirmed", blockers: [] } as never);
    vi.spyOn(actionApi, "impactCheckAction").mockResolvedValue({ status: "checked", blockers: [] } as never);
    vi.spyOn(actionApi, "applyAction").mockResolvedValue({ applied: true, status: "applied" } as never);

    renderReview();
    expect(screen.queryByRole("button", { name: "Przygotuj zamiar planowania" })).not.toBeInTheDocument();
    completeRequiredDecisionInputs();
    fireEvent.click(screen.getByRole("button", { name: "Akceptuję" }));
    expect(await screen.findByRole("button", { name: "Przygotuj zamiar planowania" }))
      .toBeInTheDocument();
  });
});
