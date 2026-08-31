from wilq.content.workflow.content_kind import (
    classify_content_kind,
    classify_content_kind_from_inventory,
    content_kind_requires_service,
)


def test_wordpress_inventory_classifies_content_without_url_heuristics() -> None:
    assert classify_content_kind("post") == "editorial"
    assert classify_content_kind("uslugi") == "service"
    assert classify_content_kind("page") == "landing_or_hub"
    assert classify_content_kind("category") == "taxonomy_or_system"
    assert classify_content_kind("unknown") == "ambiguous"


def test_only_exact_service_inventory_requires_service_binding() -> None:
    assert content_kind_requires_service("service") is True
    assert content_kind_requires_service("editorial") is False
    assert content_kind_requires_service("landing_or_hub") is None
    assert content_kind_requires_service("ambiguous") is None


def test_ambiguous_source_uses_one_exact_dev_wordpress_type() -> None:
    content_type, kind = classify_content_kind_from_inventory(
        "sitemap",
        public_url="https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
        dev_objects=[
            (
                "https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/",
                "post",
            ),
            ("https://ekologus.dev.proudsite.pl/inny-artykul/", "post"),
        ],
    )

    assert content_type == "post"
    assert kind == "editorial"


def test_conflicting_exact_dev_types_remain_ambiguous() -> None:
    content_type, kind = classify_content_kind_from_inventory(
        "sitemap",
        public_url="https://www.ekologus.pl/ten-sam-adres/",
        dev_objects=[
            ("https://ekologus.dev.proudsite.pl/ten-sam-adres/", "post"),
            ("https://ekologus.dev.proudsite.pl/ten-sam-adres/", "page"),
        ],
    )

    assert content_type == "sitemap"
    assert kind == "ambiguous"
