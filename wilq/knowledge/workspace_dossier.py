from __future__ import annotations

from wilq.schemas import WorkspaceDossier, WorkspaceDossierEntry


def build_workspace_dossier() -> WorkspaceDossier:
    """Return redacted, read-only Ekologus workspace memory for operator workflows."""
    return WorkspaceDossier(
        id="workspace_dossier:ekologus",
        workspace_id="ekologus",
        display_name="Ekologus",
        business_brief=(
            "Ekologus świadczy usługi ochrony środowiska dla firm; WILQ pomaga "
            "operatorowi wybierać pracę marketingową na podstawie dowodów."
        ),
        exclusions=[
            "ekologus.dev.proudsite.pl jest workspace WordPress, nie publicznym canonical URL",
            "brak dowodu nie pozwala tworzyć metryk, obietnic ani publikacji",
            "dossier nie wykonuje vendor writes i nie zastępuje ActionObject audit",
        ],
        source_packs=[
            WorkspaceDossierEntry(
                id="source_pack:marketing_connectors",
                title="Źródła marketingowe Ekologus",
                summary=(
                    "GSC, WordPress, Ads, GA4, Merchant, Ahrefs i Localo są "
                    "odczytywane przez WILQ."
                ),
                source_ids=[
                    "google_search_console",
                    "wordpress_ekologus",
                    "google_ads",
                    "google_analytics_4",
                    "ahrefs",
                    "google_merchant_center",
                    "localo",
                ],
            )
        ],
        previous_checks=[
            WorkspaceDossierEntry(
                id="check:daily_queue_density",
                title="Gęstość kolejki treści",
                summary=(
                    "Ostatni daily-check potwierdza, że kolejka ma za mało "
                    "propozycji gotowych do działania."
                ),
                source_ids=["content_work_item_queue"],
                status="open",
            )
        ],
        reports=[
            WorkspaceDossierEntry(
                id="report:dashboard_usefulness_2026_07_13",
                title="Dashboard usefulness review",
                summary="Render review: content marketer 8/10, technical audit 8/10, mobile 8/10.",
                source_ids=["docs/evals/dashboard-usefulness-2026-07-13.md"],
            )
        ],
        recommendation_history=[],
        client_truths=[
            WorkspaceDossierEntry(
                id="client_truth:public_dev_roles",
                title="Role public/dev WordPress",
                summary=(
                    "Publiczna domena jest SEO truth; dev służy wyłącznie do "
                    "draftów i podglądu."
                ),
                source_ids=["workspace_dossier:ekologus"],
            )
        ],
        known_false_positives=_known_false_positives(),
        open_blockers=_open_blockers(),
    )


def _known_false_positives() -> list[WorkspaceDossierEntry]:
    return [
        WorkspaceDossierEntry(
            id="known_false_positive:google_ads_account_scope",
            title="MCC/login customer nie jest kontem metryk",
            summary=(
                "Nie traktuj konta MCC/login jako źródła metryk Ekologus; "
                "przed wnioskiem sprawdź child customer scope."
            ),
            source_ids=["google_ads", "google_ads_platform_traps_v1"],
            status="known_trap",
        )
    ]


def _open_blockers() -> list[WorkspaceDossierEntry]:
    return [
        WorkspaceDossierEntry(
            id="blocker:content_candidate_density",
            title="Za mało tematów gotowych do pracy",
            summary=(
                "Kolejka contentu pozostaje zablokowana, gdy liczba "
                "evidence-backed actionable candidates jest poniżej minimum."
            ),
            source_ids=["content_work_item_queue"],
            status="open",
        ),
        WorkspaceDossierEntry(
            id="blocker:wordpress_action_apply",
            title="WordPress zapis wymaga centralnej akcji",
            summary=(
                "Preview nie jest apply; publish i destructive update "
                "pozostają zablokowane bez pełnego ActionObject audit."
            ),
            source_ids=["wordpress_ekologus", "actionobject_safety"],
            status="open",
        ),
    ]
