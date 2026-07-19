import pytest
from fastapi import HTTPException

from apps.api.wilq_api.routers.content_workflow import _reject_manual_section_map_review


def test_section_map_review_is_always_api_owned() -> None:
    with pytest.raises(HTTPException, match="wyliczana automatycznie") as error:
        _reject_manual_section_map_review()

    assert error.value.status_code == 409
