"""Executable browser-policy observer for the material-review change gate.

Delete when the change gate runs isolated Vitest directly at both Git snapshots.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def test_material_review_ui_requires_explicit_attestation_and_safe_source() -> None:
    root = Path(__file__).resolve().parents[2]
    module = root / "apps/dashboard/src/routes/ActionPanels/materialReviewDecision.ts"
    assert module.is_file(), "Current-material browser policy is absent."
    node = shutil.which("node")
    assert node is not None, "Node runtime is required for the browser contract."
    script = """
import {
  materialReviewApprovalAllowed,
  materialReviewCheckedItems,
  materialReviewPageUrl
} from "./apps/dashboard/src/routes/ActionPanels/materialReviewDecision.ts";
process.stdout.write(JSON.stringify({
  unchecked: materialReviewApprovalAllowed("approved_for_prepare", false, "https://www.ekologus.pl/a/"),
  checked: materialReviewApprovalAllowed("approved_for_prepare", true, "https://www.ekologus.pl/a/"),
  missingUrl: materialReviewApprovalAllowed("approved_for_prepare", true, null),
  rejected: materialReviewApprovalAllowed("rejected", false, null),
  checkedItems: materialReviewCheckedItems(true),
  uncheckedItems: materialReviewCheckedItems(false),
  shop: materialReviewPageUrl({public_url: "https://sklep.ekologus.pl/a/"}),
  query: materialReviewPageUrl({public_url: "https://www.ekologus.pl/a/?x=1"}),
  params: materialReviewPageUrl({public_url: "https://www.ekologus.pl/a;mode"}),
  emptyParams: materialReviewPageUrl({public_url: "https://www.ekologus.pl/a;"})
}));
"""
    result = subprocess.run(
        [node, "--experimental-strip-types", "--input-type=module", "-e", script],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-500:]
    assert json.loads(result.stdout) == {
        "unchecked": False,
        "checked": True,
        "missingUrl": False,
        "rejected": True,
        "checkedItems": ["reviewed_full_material"],
        "uncheckedItems": [],
        "shop": "https://sklep.ekologus.pl/a/",
        "query": None,
        "params": None,
        "emptyParams": "https://www.ekologus.pl/a;",
    }
