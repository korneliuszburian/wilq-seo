"""Executable packet-review observer; retire when the gate runs Vitest snapshots."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def test_packet_review_and_local_apply_require_exact_action_acknowledgement() -> None:
    root = Path(__file__).resolve().parents[2]
    module = root / "apps/dashboard/src/routes/ActionPanels/packetReviewDecision.ts"
    assert module.is_file(), "Exact packet review UI policy is absent."
    node = shutil.which("node")
    assert node is not None, "Node runtime is required for the browser contract."
    script = """
import {
  localAuthorityApplyAllowed,
  packetReviewApprovalAllowed,
  packetReviewCheckedItems
} from "./apps/dashboard/src/routes/ActionPanels/packetReviewDecision.ts";
process.stdout.write(JSON.stringify({
  beforeReview: packetReviewApprovalAllowed("approved_for_prepare", "act_a", null, true),
  wrongAction: packetReviewApprovalAllowed("approved_for_prepare", "act_b", "act_a", true),
  hiddenPacket: packetReviewApprovalAllowed("approved_for_prepare", "act_a", "act_a", false),
  reviewed: packetReviewApprovalAllowed("approved_for_prepare", "act_a", "act_a", true),
  checkedItems: packetReviewCheckedItems("act_a", "act_a"),
  foreignItems: packetReviewCheckedItems("act_b", "act_a"),
  beforeApply: localAuthorityApplyAllowed("act_a", null, true),
  blockedGate: localAuthorityApplyAllowed("act_a", "act_a", false),
  foreignApply: localAuthorityApplyAllowed("act_b", "act_a", true),
  exactApply: localAuthorityApplyAllowed("act_a", "act_a", true)
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
        "beforeReview": False,
        "wrongAction": False,
        "hiddenPacket": False,
        "reviewed": True,
        "checkedItems": ["reviewed_full_packet"],
        "foreignItems": [],
        "beforeApply": False,
        "blockedGate": False,
        "foreignApply": False,
        "exactApply": True,
    }
