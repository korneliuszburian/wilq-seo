import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { readFileSync } from "node:fs";
import type { ReactElement, ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ActionObject } from "../lib/api";
import * as actionApi from "../lib/api";
import { ActionFocus, ActionReviewGatePanel, ActionValidationControls } from "./ActionPanels";
import { ActionHumanReviewControls } from "./ActionPanels/ReviewControls";

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    params
  }: {
    children: ReactNode;
    params?: { actionId?: string; evidenceId?: string };
  }) => {
    const id = params?.actionId ?? params?.evidenceId ?? "";
    const prefix = params?.actionId ? "/actions/" : "/evidence/";
    return <a href={`${prefix}${id}`}>{children}</a>;
  }
}));

describe("ActionPanels", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("applies only the reviewed local packet receipt after a separate confirmation", async () => {
    const apply = vi.spyOn(actionApi, "applyAction").mockImplementation(
      () => new Promise<never>(() => {})
    );
    const action = {
      id: "act_content_research_packet_v2_exact",
      payload: {
        action_type: "content_research_packet_v2_approval",
        local_authority_only: true
      },
      review_gate: { status: "ready_to_apply", apply_allowed: true }
    } as unknown as ActionObject;

    renderWithQueryClient(<ActionValidationControls action={action} />);
    const save = screen.getByRole("button", { name: "Zapisz lokalny receipt pakietu" });
    expect(save).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: /Potwierdzam dokładny review pakietu/ }));
    expect(save).toBeEnabled();
    fireEvent.click(save);
    await waitFor(() => expect(apply).toHaveBeenCalledWith(action.id, {
      confirm: true,
      confirmed_by: "operator_local_dashboard"
    }));
  });

  it("offers a local material receipt write without a WordPress draft payload", async () => {
    const apply = vi.spyOn(actionApi, "applyAction").mockImplementation(
      () => new Promise<never>(() => {})
    );
    const action = {
      id: "act_content_material_review_exact",
      payload: { action_type: "content_current_material_review_v2", local_authority_only: true },
      review_gate: { status: "ready_to_apply", apply_allowed: true }
    } as unknown as ActionObject;
    renderWithQueryClient(<ActionValidationControls action={action} />);
    const save = screen.getByRole("button", { name: "Zapisz lokalny review materiału" });
    expect(save).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: /Potwierdzam dokładny review materiału/ }));
    fireEvent.click(save);
    await waitFor(() => expect(apply).toHaveBeenCalledWith(action.id, {
      confirm: true,
      confirmed_by: "operator_local_dashboard"
    }));
  });

  it("requires an explicit full-material check before approving current material", async () => {
    const review = vi.spyOn(actionApi, "reviewAction").mockImplementation(
      () => new Promise<never>(() => {})
    );
    const action = {
      id: "act_content_material_review_exact",
      payload: {
        action_type: "content_current_material_review_v2",
        material_review_preview: {
          public_url: "https://www.ekologus.pl/oferta/bdo/"
        }
      },
      review_gate: {
        status: "ready_to_apply",
        status_label: "gotowe",
        operator_checklist: ["validate_action_object", "human_review_before_apply"],
        apply_blockers: []
      }
    } as unknown as ActionObject;

    renderWithQueryClient(<ActionHumanReviewControls action={action} />);
    const save = screen.getByRole("button", { name: "Zapisz przegląd" });
    expect(save).toBeDisabled();
    expect(screen.getByRole("link", { name: "Otwórz pełny materiał strony" })).toHaveAttribute(
      "href",
      "https://www.ekologus.pl/oferta/bdo/"
    );
    fireEvent.click(screen.getByRole("checkbox", { name: /Przeczytałem pełny materiał/ }));
    expect(save).toBeEnabled();
    fireEvent.click(save);
    await waitFor(() => {
      expect(review).toHaveBeenCalledWith(action.id, expect.objectContaining({
        outcome: "approved_for_prepare",
        checked_items: ["reviewed_full_material"]
      }));
    });
  });

  it("uses the exact public source-host policy for material review links", () => {
    const actionForUrl = (url: string) => ({
      id: "act_content_material_review_exact",
      payload: {
        action_type: "content_current_material_review_v2",
        material_review_preview: { public_url: url }
      },
      review_gate: {
        status: "ready_to_apply",
        status_label: "gotowe",
        operator_checklist: [],
        apply_blockers: []
      }
    } as unknown as ActionObject);

    for (const url of [
      "https://www.ekologus.pl/oferta/bdo/?x=1",
      "https://www.ekologus.pl/oferta/bdo/#plan",
      "https://www.ekologus.pl:443/oferta/bdo/",
      "https://www.ekologus.pl/oferta/bdo;mode",
      "https://www.ekologus.pl/oferta/\u0001bdo/",
      "https://www.ekologus.pl/oferta/\u007fbdo/"
    ]) {
      const view = renderWithQueryClient(<ActionHumanReviewControls action={actionForUrl(url)} />);
      expect(screen.queryByRole("link", { name: "Otwórz pełny materiał strony" })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Zapisz przegląd" })).toBeDisabled();
      view.unmount();
    }

    renderWithQueryClient(
      <ActionHumanReviewControls action={actionForUrl("https://sklep.ekologus.pl/oferta/bdo/")} />
    );
    expect(screen.getByRole("link", { name: "Otwórz pełny materiał strony" })).toHaveAttribute(
      "href",
      "https://sklep.ekologus.pl/oferta/bdo/"
    );
    fireEvent.click(screen.getByRole("checkbox", { name: /Przeczytałem pełny materiał/ }));
    expect(screen.getByRole("button", { name: "Zapisz przegląd" })).toBeEnabled();
    cleanup();

    renderWithQueryClient(
      <ActionHumanReviewControls action={actionForUrl("https://www.ekologus.pl/oferta/bdo;")} />
    );
    expect(screen.getByRole("link", { name: "Otwórz pełny materiał strony" })).toHaveAttribute(
      "href",
      "https://www.ekologus.pl/oferta/bdo;"
    );
  });

  it("requires a separate full-packet attestation and shows reviewed facts", async () => {
    const review = vi.spyOn(actionApi, "reviewAction").mockImplementation(
      () => new Promise<never>(() => {})
    );
    const packet = {
      schema_version: "wilq_research_packet_v2_preview_record_v1",
      preview_hash: "a".repeat(64),
      work_item_id: "wi_exact",
      snapshot: {
        status: "ready",
        work_item_id: "wi_exact",
        preview_hash: "a".repeat(64),
        source_pack_hash: "b".repeat(64),
        selected_facts: [{
          source_fact_id: "fact_exact",
          text: "Dokładny zatwierdzony fakt.",
          source_reference: "https://eur-lex.europa.eu/eli/reg/2025/40/oj/pol",
          freshness_date: "2026-09-23",
          source_type: "legal_update",
          source_connectors: ["official_regulatory_review"],
          fact_digest: "c".repeat(64),
          evidence_ids: ["ev_fact_exact"]
        }],
        planning_context: {
          target_reader: "Przedsiębiorca",
          buyer_problem: "Niejasny obowiązek",
          buyer_trigger: "Zmiana prawa",
          search_intent: "Sprawdzenie obowiązku"
        },
        legal_requirements: [{
          requirement_id: "requirement_exact",
          label: "Dokumentacja",
          source_fact_ids: ["fact_exact"],
          evidence_ids: ["ev_fact_exact"]
        }],
        regulatory_profile_id: "profile_exact",
        regulatory_profile_version: "2026-09",
        cta_direction: "Kontakt z doradcą",
        minimum_cta_blocks: 2,
        required_cta_patterns: ["kontakt"],
        internal_links: [{
          target_url: "https://www.ekologus.pl/kontakt/",
          anchor_hint: "Kontakt",
          evidence_ids: ["ev_link"]
        }],
        evidence_ids: ["ev_fact_exact", "ev_link"],
        generation_allowed: false,
        packet_write_allowed: false
      }
    };
    const action = {
      id: "act_content_research_packet_v2_exact",
      payload: { action_type: "content_research_packet_v2_approval", research_packet_v2_preview: packet },
      review_gate: {
        status: "ready_to_apply",
        status_label: "gotowe",
        operator_checklist: ["validate_action_object", "human_review_before_apply"],
        apply_blockers: []
      }
    } as unknown as ActionObject;

    const view = renderWithQueryClient(<ActionHumanReviewControls action={action} />);
    const save = screen.getByRole("button", { name: "Zapisz przegląd" });
    expect(save).toBeDisabled();
    expect(screen.getByText("Dokładny zatwierdzony fakt.")).toBeInTheDocument();
    expect(screen.getByText(/^fact_exact$/)).toBeInTheDocument();
    expect(screen.getByText("Dokumentacja")).toBeInTheDocument();
    expect(screen.getByText(/Profil: profile_exact, wersja 2026-09/)).toBeInTheDocument();
    expect(screen.getByText(/Minimalna liczba bloków CTA: 2/)).toBeInTheDocument();
    expect(screen.getByText(/Dowody linku: ev_link/)).toBeInTheDocument();
    expect(screen.getByText(/Dowody całego pakietu: ev_fact_exact, ev_link/)).toBeInTheDocument();
    view.rerender(
      <QueryClientProvider client={new QueryClient()}>
        <ActionHumanReviewControls action={{
          ...action,
          payload: {
            ...action.payload,
            research_packet_v2_preview: {
              ...packet,
              snapshot: { ...packet.snapshot, legal_requirements: [] }
            }
          }
        }} />
      </QueryClientProvider>
    );
    expect(screen.getByText(/Profil: profile_exact, wersja 2026-09/)).toBeInTheDocument();
    view.rerender(
      <QueryClientProvider client={new QueryClient()}>
        <ActionHumanReviewControls action={action} />
      </QueryClientProvider>
    );
    fireEvent.click(screen.getByRole("checkbox", { name: /Przeczytałem cały pakiet/ }));
    expect(save).toBeEnabled();
    view.rerender(
      <QueryClientProvider client={new QueryClient()}>
        <ActionHumanReviewControls action={{ ...action, id: "act_content_research_packet_v2_other" }} />
      </QueryClientProvider>
    );
    expect(screen.getByRole("button", { name: "Zapisz przegląd" })).toBeDisabled();
    view.rerender(
      <QueryClientProvider client={new QueryClient()}>
        <ActionHumanReviewControls action={action} />
      </QueryClientProvider>
    );
    fireEvent.click(screen.getByRole("button", { name: "Zapisz przegląd" }));
    await waitFor(() => expect(review).toHaveBeenCalledWith(action.id, expect.objectContaining({
      checked_items: ["reviewed_full_packet"]
    })));
  });

  it("threads the exact dev-draft binding through every action control", async () => {
    const binding = {
      work_item_id: "content_work_item_bdo",
      handoff_id: "wordpress_draft_handoff_content_work_item_bdo_revision_1",
      revision_id: "revision_1",
      content_digest: "a".repeat(64),
      draft_package_id: "draft_package_1",
      draft_package_digest: "b".repeat(64),
      planning_digest: "c".repeat(64),
      approval_decision_id: "decision_1",
      final_canonical_url: "https://ekologus.pl/bdo/"
    };
    const pending = () => new Promise<never>(() => {});
    const preview = vi.spyOn(actionApi, "previewAction").mockImplementation(pending);
    const review = vi.spyOn(actionApi, "reviewAction").mockImplementation(pending);
    const confirm = vi.spyOn(actionApi, "confirmAction").mockImplementation(pending);
    const impact = vi.spyOn(actionApi, "impactCheckAction").mockImplementation(pending);
    const apply = vi.spyOn(actionApi, "applyAction").mockImplementation(pending);
    const action = {
      id: "act_content_dev_draft_test",
      title: "Utwórz szkic dev",
      domain: "content",
      connector: "wordpress_ekologus",
      connector_label: "WordPress",
      mode: "apply",
      mode_label: "zapis",
      risk: "medium",
      risk_label: "średnie ryzyko",
      status: "ready",
      status_label: "gotowe",
      evidence_ids: ["ev_test"],
      evidence_summary_label: "1 dowód",
      metrics: [],
      human_diagnosis: "Exact rewizja jest gotowa.",
      recommended_reason: "Utwórz jeden szkic.",
      validation_status: "valid",
      validation_status_label: "poprawna",
      review_gate: {
        status: "ready_to_apply",
        status_label: "gotowe",
        summary: "Gotowe.",
        required_checks: [],
        required_check_labels: [],
        operator_checklist: ["exact_document_revision_check"],
        operator_checklist_labels: ["dokładna wersja"],
        apply_blockers: [],
        apply_blocker_labels: [],
        apply_blocker_summary_label: "brak blokad",
        confirmation_required: true,
        apply_allowed: true
      },
      preview_cards: [],
      payload: {
        action_type: "content_dev_draft_create",
        wordpress_draft_binding: binding,
        payload_preview: []
      },
      audit_events: []
    } as unknown as ActionObject;

    renderWithQueryClient(<ActionFocus actions={[action]} />);
    const lifecycleButtons = [
      "Sprawdź w WILQ",
      "Generuj podgląd",
      "Zapisz przegląd",
      "Potwierdź podgląd",
      "Sprawdź efekt"
    ].map((name) => screen.getByRole("button", { name }));
    for (let index = 0; index < lifecycleButtons.length - 1; index += 1) {
      expect(lifecycleButtons[index]?.compareDocumentPosition(lifecycleButtons[index + 1]!))
        .toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    }
    fireEvent.click(screen.getByRole("button", { name: "Generuj podgląd" }));
    fireEvent.click(screen.getByRole("button", { name: "Zapisz przegląd" }));
    fireEvent.click(screen.getByRole("button", { name: "Potwierdź podgląd" }));
    fireEvent.click(screen.getByRole("button", { name: "Sprawdź efekt" }));
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Potwierdzam exact binding, podgląd, review i kontrolę gotowości szkicu."
      })
    );
    fireEvent.click(screen.getByRole("button", { name: "Utwórz szkic treści na dev" }));

    await waitFor(() => {
      expect(preview).toHaveBeenCalledWith(action.id, expect.objectContaining({
        wordpress_draft: binding
      }));
      expect(review).toHaveBeenCalledWith(action.id, expect.objectContaining({
        wordpress_draft: binding
      }));
      expect(confirm).toHaveBeenCalledWith(action.id, expect.objectContaining({
        wordpress_draft: binding
      }));
      expect(impact).toHaveBeenCalledWith(action.id, expect.objectContaining({
        wordpress_draft: binding
      }));
      expect(apply).toHaveBeenCalledWith(action.id, {
        confirm: true,
        confirmed_by: "operator_local_dashboard",
        wordpress_draft: binding
      });
    });
  });

  it("shows the safety record without audit or adapter jargon", () => {
    render(
      <ActionReviewGatePanel
        action={
          {
            review_gate: {
              status: "pending_validation",
              operator_checklist: ["preview_payload_required"],
              operator_checklist_labels: ["sprawdź podgląd zmian"],
              apply_blockers: ["vendor_mutation_adapter_required"],
              apply_blocker_labels: ["brak bezpiecznej ścieżki zapisu w zewnętrznym systemie"],
              apply_blocker_summary_label: "1 blokada",
              confirmation_required: true,
              apply_allowed: false,
              last_confirmation_summary: null,
              last_mutation_audit_summary: "blocked",
              last_mutation_audit_status: "blocked",
              last_mutation_audit_status_label: "zablokowany",
              last_mutation_adapter_reached: false,
              last_mutation_adapter_reached_label: "adapter wykonania nie został osiągnięty",
              last_external_write_attempted: false,
              last_external_write_attempted_label: "nie próbowano zapisu w systemie zewnętrznym",
              last_mutation_attempted: false,
              last_mutation_attempted_label: "nie próbowano zapisu w systemie zewnętrznym",
              last_mutation_adapter: null,
              last_mutation_adapter_label: "brak bezpiecznej ścieżki zapisu",
              last_mutation_audit_event_id: "audit_apply_blocked",
              last_mutation_audit_trace_label: "ślad bezpieczeństwa zapisany",
              last_mutation_blockers: ["vendor_mutation_adapter_required"],
              last_mutation_blocker_labels: ["brak bezpiecznej ścieżki zapisu w zewnętrznym systemie"],
              last_mutation_blocker_summary_label: "1 blokada"
            }
          } as ActionObject
        }
      />
    );

    expect(screen.getByText("Ostatni zapis bezpieczeństwa")).toBeInTheDocument();
    expect(
      screen.getByText("Zapisano kontrolę bezpieczeństwa bez zmian w zewnętrznych systemach.")
    ).toBeInTheDocument();
    expect(screen.getByText("Wynik: zablokowany")).toBeInTheDocument();
    expect(
      screen.getByText("Czy próbowano zapisu: nie próbowano zapisu w systemie zewnętrznym")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Granica adaptera: adapter wykonania nie został osiągnięty")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Vendor write: nie próbowano zapisu w systemie zewnętrznym")
    ).toBeInTheDocument();
    expect(screen.getByText("System zewnętrzny: brak bezpiecznej ścieżki zapisu")).toBeInTheDocument();
    expect(screen.getByText("Ślad bezpieczeństwa: ślad bezpieczeństwa zapisany")).toBeInTheDocument();
    expect(screen.getAllByText(/1 blokada/).length).toBeGreaterThan(0);
    expect(screen.queryByText("Wynik: brak")).not.toBeInTheDocument();
    expect(screen.queryByText("System zewnętrzny: brak")).not.toBeInTheDocument();
    expect(screen.queryByText("Ślad bezpieczeństwa: brak")).not.toBeInTheDocument();
    expect(screen.queryByText(/vendor_mutation_adapter_required/)).not.toBeInTheDocument();
    expect(screen.queryByText("Ostatni audyt zmiany")).not.toBeInTheDocument();
    expect(screen.queryByText(/Adapter:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Zdarzenie audytu:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Próba zmiany:/)).not.toBeInTheDocument();
    expect(screen.queryByText("Utworzono szkic")).not.toBeInTheDocument();
  });

  it("shows where the verified WordPress draft was created", () => {
    render(
      <ActionReviewGatePanel
        action={
          {
            id: "act_apply_wordpress_draft_handoff",
            title: "Przekaż szkic na dev",
            domain: "wordpress",
            connector: "wordpress_ekologus",
            connector_label: "WordPress",
            mode: "apply",
            mode_label: "zapis",
            risk: "medium",
            risk_label: "średnie ryzyko",
            status: "applied",
            status_label: "zastosowano",
            evidence_ids: [],
            evidence_summary_label: "",
            metrics: [],
            human_diagnosis: "Szkic utworzony.",
            recommended_reason: "",
            validation_status: "valid",
            validation_status_label: "poprawna",
            review_gate: {
              status: "ready_to_apply",
              status_label: "gotowe",
              operator_checklist_labels: [],
              apply_blocker_summary_label: "brak blokad",
              confirmation_required: true,
              apply_allowed: true,
              last_confirmation_summary: "Potwierdzono.",
              last_mutation_audit_summary: "applied",
              last_mutation_audit_status_label: "zastosowano",
              last_mutation_attempted: true,
              last_mutation_attempted_label: "wykonano zapis",
              last_mutation_adapter_reached_label: "adapter osiągnięty",
              last_external_write_attempted_label: "wykonano zapis",
              last_mutation_adapter_label: "WordPress",
              last_mutation_audit_trace_label: "ślad zapisany",
              last_mutation_blocker_summary_label: "brak blokad"
            },
            preview_cards: [],
            payload: {},
            audit_events: []
          } as unknown as ActionObject
        }
        lastCreatedDraft={{
          wordpress_post_id: "1275",
          post_status: "draft",
          readback_status: "available",
          blocker_code: null,
          blocker_label: "",
          link: "https://ekologus.dev.proudsite.pl/?p=1275",
          edit_link:
            "https://ekologus.dev.proudsite.pl/wp-admin/post.php?post=1275&action=edit",
          modified_gmt: "2026-08-08T10:15:00",
          content_digest: "a".repeat(64),
          verification_status: "verified"
        }}
      />
    );

    expect(screen.getByText("Utworzono szkic")).toBeInTheDocument();
    expect(screen.getByText("Utworzono szkic")).toHaveClass("text-success");
    expect(screen.getByText("post_id: 1275")).toBeInTheDocument();
    expect(screen.getByText("modified_gmt: 2026-08-08T10:15:00")).toBeInTheDocument();
    expect(screen.getByText("Potwierdzenie digestu: zweryfikowany")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Szkic nie jest publicznie widoczny do czasu publikacji (poza zakresem WILQ)."
      )
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Otwórz link publiczny" })).toHaveAttribute(
      "href",
      "https://ekologus.dev.proudsite.pl/?p=1275"
    );
    expect(screen.getByRole("link", { name: "Otwórz w edytorze WordPress" }))
      .toHaveAttribute(
        "href",
        "https://ekologus.dev.proudsite.pl/wp-admin/post.php?post=1275&action=edit"
      );
    expect(screen.getByRole("link", { name: "Otwórz w edytorze WordPress" }))
      .toHaveAttribute("target", "_blank");
    expect(screen.getByRole("link", { name: "Otwórz w edytorze WordPress" }))
      .toHaveAttribute("rel", "noreferrer");
  });

  it("warns when the WordPress readback reports a published post", () => {
    render(
      <ActionReviewGatePanel
        action={
          {
            review_gate: {
              status: "ready_to_apply",
              operator_checklist_labels: [],
              apply_blocker_summary_label: "brak blokad",
              confirmation_required: true,
              apply_allowed: true,
              last_confirmation_summary: null,
              last_mutation_audit_summary: null
            }
          } as unknown as ActionObject
        }
        lastCreatedDraft={{
          wordpress_post_id: "1275",
          post_status: "publish",
          readback_status: "blocked",
          blocker_code: "wordpress_draft_status_mismatch",
          blocker_label: "Odczyt nie potwierdził statusu draft",
          link: "https://ekologus.dev.proudsite.pl/?p=1275",
          edit_link:
            "https://ekologus.dev.proudsite.pl/wp-admin/post.php?post=1275&action=edit",
          modified_gmt: "2026-08-08T10:15:00",
          content_digest: "a".repeat(64),
          verification_status: "blocked"
        }}
      />
    );

    expect(screen.queryByText("Utworzono szkic")).not.toBeInTheDocument();
    expect(screen.getByText("Status szkicu wymaga sprawdzenia")).toHaveClass("text-risk");
    expect(
      screen.getByText(
        "Szkic ma status: publish — sprawdź, zanim założysz, że nie jest publiczny."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        "Szkic nie jest publicznie widoczny do czasu publikacji (poza zakresem WILQ)."
      )
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("Blokada odczytu: Odczyt nie potwierdził statusu draft")
    ).toBeInTheDocument();
  });

  it("does not render links for foreign, insecure, or credential-bearing URLs", () => {
    render(
      <ActionReviewGatePanel
        action={{
          review_gate: {
            status: "ready_to_apply",
            operator_checklist_labels: [],
            apply_blocker_summary_label: "brak blokad",
            confirmation_required: true,
            apply_allowed: true,
            last_confirmation_summary: null,
            last_mutation_audit_summary: null
          }
        } as unknown as ActionObject}
        lastCreatedDraft={{
          wordpress_post_id: "1275",
          post_status: "draft",
          readback_status: "blocked",
          blocker_code: "wordpress_draft_verification_unavailable",
          blocker_label: "Treść wymaga sprawdzenia",
          link: "https://attacker.example/?p=1275",
          edit_link: (
            "http://" + "user:" + "password" + "@ekologus.dev.proudsite.pl/"
            + "wp-admin/post.php?post=1275&action=edit"
          ),
          modified_gmt: "",
          content_digest: "",
          verification_status: "blocked"
        }}
      />
    );

    expect(screen.getByText("post_id: 1275")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Otwórz link publiczny" }))
      .not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Otwórz w edytorze WordPress" }))
      .not.toBeInTheDocument();
  });

  it("uses the action evidence summary as visible proof context", () => {
    renderWithQueryClient(
      <ActionFocus
        actions={[
          {
            id: "action_merchant_feed_review",
            title: "Sprawdź feed produktowy",
            domain: "merchant",
            connector: "merchant_center",
            connector_label: "Merchant Center",
            mode: "prepare",
            mode_label: "przygotowanie",
            risk: "medium",
            risk_label: "średnie ryzyko",
            status: "needs_validation",
            status_label: "do sprawdzenia",
            evidence_ids: ["evidence_merchant_feed_status", "evidence_merchant_policy_status"],
            evidence_summary_label: "2 dowody źródłowe",
            metrics: [],
            human_diagnosis: "Feed wymaga sprawdzenia przed zmianami.",
            recommended_reason: "WILQ ma dowody z Merchant Center.",
            validation_status: "not_validated",
            validation_status_label: "niezwalidowana",
            review_gate: {
              status: "pending_validation",
              status_label: "wymaga sprawdzenia",
              summary: "Wymaga sprawdzenia w WILQ przed kolejnym krokiem.",
              required_checks: [],
              required_check_labels: [],
              operator_checklist: ["preview_payload_required"],
              operator_checklist_labels: ["sprawdź podgląd zmian"],
              apply_blockers: ["vendor_mutation_adapter_required"],
              apply_blocker_labels: ["brak bezpiecznej ścieżki zapisu"],
              apply_blocker_summary_label: "1 blokada",
              confirmation_required: true,
              apply_allowed: false,
              last_mutation_blockers: [],
              last_mutation_blocker_labels: [],
              last_mutation_blocker_summary_label: "brak blokad"
            },
            preview_cards: [],
            payload: { raw_debug_value: "wartość tylko do audytu" },
            audit_events: []
          } as ActionObject
        ]}
      />
    );

    expect(screen.getByText("2 dowody źródłowe")).toBeInTheDocument();
    expect(screen.getByText("Źródła danych: Merchant Center")).toBeInTheDocument();
    expect(screen.getByText("Tryb pracy: przygotowanie")).toBeInTheDocument();
    expect(screen.getByText("Co sprawdzić przed decyzją")).toBeInTheDocument();
    expect(screen.getByText("WILQ ma dowody z Merchant Center.")).toBeInTheDocument();
    expect(screen.getByText(/Najpierw sprawdź/)).toBeInTheDocument();
    expect(screen.getAllByText(/sprawdź podgląd zmian/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Przed zapisem blokuje/)).toBeInTheDocument();
    expect(screen.getAllByText(/1 blokada/).length).toBeGreaterThan(0);
    expect(screen.queryByText("Merchant Center / przygotowanie")).not.toBeInTheDocument();
    expect(screen.queryByText("evidence_merchant_feed_status")).not.toBeInTheDocument();
    expect(screen.queryByText("evidence_merchant_policy_status")).not.toBeInTheDocument();
    expect(screen.queryByText(/vendor_mutation_adapter_required/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "dowód 1" })).toHaveAttribute(
      "href",
      "/evidence/evidence_merchant_feed_status"
    );
    expect(screen.getByRole("link", { name: "dowód 2" })).toHaveAttribute(
      "href",
      "/evidence/evidence_merchant_policy_status"
    );
    expect(screen.queryByText(/Domyślnie schowany/)).not.toBeInTheDocument();
    expect(screen.queryByText(/wartość tylko do audytu/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż dane techniczne akcji" }));

    expect(screen.getByText(/Domyślnie schowany/)).toBeInTheDocument();
    expect(screen.getByText(/wartość tylko do audytu/)).toBeInTheDocument();
  });

  it("does not join action metadata with slash copy", () => {
    const source = readFileSync("src/routes/ActionPanels.tsx", "utf8");
    expect(source).not.toContain("{action.connector_label} / {action.mode_label}");
  });

  it("keeps raw action data drawer named as technical detail, not payload preview", () => {
    const source = readFileSync("src/routes/ActionPanels.tsx", "utf8");
    expect(source).toContain("ActionTechnicalDataToggle");
    expect(source).toContain("technicalData={action.payload}");
    expect(source).not.toContain("ActionPayloadPreviewToggle");
    expect(source).not.toContain("payload={action.payload}");
  });

  it("keeps review badge state separate from visible review copy", () => {
    const source = readFileSync("src/routes/ActionPanels/ReviewControls.tsx", "utf8");
    expect(source).toContain(
      "action.review_gate.last_review_outcome_label ?? action.review_gate.status_label"
    );
    expect(source).toContain(
      "value={action.review_gate.status} label={reviewStatusLabel}"
    );
    expect(source).not.toContain('"brak przeglądu"');
    expect(source).not.toContain('value={lastReviewLabel ?? "brak przeglądu"}');
  });

  it("does not assemble action count copy from action IDs", () => {
    const source = readFileSync("src/routes/ActionPanels.tsx", "utf8");
    expect(source).toContain("actionSummaryLabel");
    expect(source).not.toContain("actionIds.length === 1");
    expect(source).not.toContain("`${actionIds.length} akcji do sprawdzenia`");
  });

  it("keeps effect checks in plain comparison language", () => {
    const source = readFileSync("src/routes/ActionPanels/ValidationApplyControls.tsx", "utf8");
    expect(source).toContain("porównanie wyników sprzed zmiany i po zmianie");
    expect(source).not.toContain("okno efektu");
    expect(source).not.toContain("Zapisuje okno");
    expect(source).not.toContain("Okna:");
  });

  it("uses self-defending empty states instead of bare brak placeholders", () => {
    const source = [
      "src/routes/ActionPanels.tsx",
      "src/routes/ActionPanels/PreviewControls.tsx",
      "src/routes/ActionPanels/ValidationApplyControls.tsx",
      "src/routes/ActionPanels/GatePanel.tsx"
    ]
      .map((path) => readFileSync(path, "utf8"))
      .join("\n");
    expect(source).not.toContain('empty="brak etykiety dowodów z WILQ"');
    expect(source).not.toContain('empty="brak blokad podglądu"');
    expect(source).not.toContain('empty="brak dodatkowych warunków"');
    expect(source).not.toContain('empty="brak błędów"');
    expect(source).not.toContain('empty="brak ostrzeżeń"');
    expect(source).not.toContain('empty="brak blokad potwierdzenia"');
    expect(source).not.toMatch(/empty="brak (źródeł|dowodów)/);
    expect(source).not.toMatch(/"brak dowodów/);
    expect(source).toContain("nie traktuj tej akcji jako gotowej rekomendacji");
    expect(source).toContain("WILQ nie zgłosił blokad podglądu");
    expect(source).toContain("WILQ nie zgłosił błędów sprawdzenia");
    expect(source).toContain("nie oceniaj efektu bez źródła");
  });

  it("renders API-owned action preview cards instead of assembling copy from the payload", () => {
    renderWithQueryClient(
      <ActionFocus
        actions={[
          {
            id: "action_ads_review",
            title: "Sprawdź kampanie Ads",
            domain: "ads",
            connector: "google_ads",
            connector_label: "Google Ads",
            mode: "prepare",
            mode_label: "przygotowanie",
            risk: "high",
            risk_label: "wysokie ryzyko",
            status: "ready",
            status_label: "gotowe",
            evidence_ids: ["evidence_ads"],
            evidence_summary_label: "1 dowód",
            metrics: [],
            human_diagnosis: "Są kampanie do review.",
            recommended_reason: "WILQ ma dowody.",
            validation_status: "valid",
            validation_status_label: "poprawna",
            review_gate: {
              status: "pending_validation",
              status_label: "wymaga sprawdzenia",
              summary: "Wymaga sprawdzenia w WILQ.",
              operator_checklist_labels: [],
              apply_blocker_summary_label: "brak blokad",
              confirmation_required: true,
              apply_allowed: false,
              last_mutation_blockers: [],
              last_mutation_blocker_labels: [],
              last_mutation_blocker_summary_label: "brak blokad"
            },
            preview_cards: [
              {
                id: "card_campaign_bdo",
                title_label: "Kampania BDO",
                subtitle_label: "Google Ads",
                status_label: "do review",
                rows: [{ label: "Priorytet", value: "najpierw" }],
                apply_state_label: "",
                system_readiness_label: ""
              }
            ],
            payload: { campaign_candidates: [{ campaign_name: "tylko-w-payloadzie" }] },
            audit_events: []
          } as unknown as ActionObject
        ]}
      />
    );

    expect(screen.getByText("Kampania BDO")).toBeInTheDocument();
    expect(screen.getByText(/Priorytet: najpierw/)).toBeInTheDocument();
    expect(screen.queryByText(/tylko-w-payloadzie/)).not.toBeInTheDocument();
    expect(screen.queryByText("Co obejmuje akcja")).not.toBeInTheDocument();
  });
});

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}
