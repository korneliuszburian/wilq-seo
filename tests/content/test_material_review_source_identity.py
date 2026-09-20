from wilq.content.workflow.material_review import (
    _canonical_material_source,
    material_review_source_field_lineage_digest,
)


def test_exact_rest_and_bounded_article_html_share_material_source_identity() -> None:
    rest = "wordpress_rest.content"
    html = "public_html.article_content"

    assert _canonical_material_source(rest) == _canonical_material_source(html)
    assert material_review_source_field_lineage_digest([rest]) == (
        material_review_source_field_lineage_digest([html])
    )
    assert _canonical_material_source("public_html.main") != _canonical_material_source(rest)
