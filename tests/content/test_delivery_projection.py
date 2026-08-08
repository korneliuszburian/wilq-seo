import pytest

from wilq.content.workflow.workspace.delivery_projection import wordpress_post_content_html


def test_wordpress_post_content_rejects_document_without_leading_h1() -> None:
    document_html = "<div><p>Wrapper renderera.</p><h1>BDO</h1></div>"

    with pytest.raises(ValueError, match="zaczynać się od elementu h1"):
        wordpress_post_content_html(document_html)
