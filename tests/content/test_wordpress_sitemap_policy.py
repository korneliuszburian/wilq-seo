from wilq.connectors.wordpress.sitemap_policy import (
    sitemap_entry_policy,
    sitemap_group_for_url,
    sitemap_url_object,
    wordpress_post_type_for_sitemap_group,
)


def test_sitemap_policy_separates_editorial_and_commerce_maps() -> None:
    assert sitemap_group_for_url("https://ekologus.pl/post-sitemap.xml") == "posts"
    assert sitemap_group_for_url("https://ekologus.pl/page-sitemap.xml") == "pages"
    assert sitemap_group_for_url("https://ekologus.pl/product-sitemap.xml") == "products"
    assert sitemap_group_for_url("https://ekologus.pl/product_cat-sitemap.xml") == "product_cat"
    assert sitemap_entry_policy("pages") == ("true", "editorial")
    assert sitemap_entry_policy("products") == ("false", "commerce_catalog")
    assert sitemap_entry_policy("product_cat") == ("false", "commerce_catalog")
    assert wordpress_post_type_for_sitemap_group("posts") == "post"
    assert wordpress_post_type_for_sitemap_group("pages") == "page"
    assert wordpress_post_type_for_sitemap_group("uslugi") == "uslugi"
    assert wordpress_post_type_for_sitemap_group("category") is None


def test_dev_content_maps_are_editorial_but_taxonomies_are_not() -> None:
    assert sitemap_group_for_url("https://ekologus.dev.proudsite.pl/uslugi-sitemap.xml") == "uslugi"
    assert sitemap_entry_policy("uslugi") == ("true", "editorial")
    assert sitemap_group_for_url(
        "https://ekologus.dev.proudsite.pl/szkolenia_otwarte-sitemap.xml"
    ) == "szkolenia_otwarte"
    assert sitemap_entry_policy("category") == ("false", "taxonomy")


def test_legacy_shop_and_sorbent_urls_stay_out_of_editorial_inventory() -> None:
    for url in (
        "https://www.ekologus.pl/sorbenty-czym-sa-jak-dzialaja/",
        "https://www.ekologus.pl/sorbenty/mata-sorpcyjna-cienka-gladka-5/",
        "https://www.ekologus.pl/oferta/sprzedaz-sorbentow/",
        "https://sklep.ekologus.pl/produkt/mata-sorpcyjna/",
    ):
        item = sitemap_url_object({"loc": url}, metadata_group="posts")
        assert item["editorial_eligible"] == "false"
        assert item["inventory_scope"] == "commerce_catalog"
