from wilq.connectors.wordpress.sitemap_policy import (
    sitemap_entry_policy,
    sitemap_group_for_url,
)


def test_sitemap_policy_separates_editorial_and_commerce_maps() -> None:
    assert sitemap_group_for_url("https://ekologus.pl/post-sitemap.xml") == "posts"
    assert sitemap_group_for_url("https://ekologus.pl/page-sitemap.xml") == "pages"
    assert sitemap_group_for_url("https://ekologus.pl/product-sitemap.xml") == "products"
    assert sitemap_group_for_url("https://ekologus.pl/product_cat-sitemap.xml") == "product_cat"
    assert sitemap_entry_policy("pages") == ("true", "editorial")
    assert sitemap_entry_policy("products") == ("false", "commerce_catalog")
    assert sitemap_entry_policy("product_cat") == ("false", "commerce_catalog")
