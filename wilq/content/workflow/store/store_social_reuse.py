from __future__ import annotations

import json
import sqlite3
from typing import cast

from wilq.security.redaction import redact_mapping
from wilq.social.reuse import SocialReuseProposal, SocialReuseReview
from wilq.storage.model_json import model_json as _model_json


class _SocialReuseStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def save_social_reuse_proposal(self, proposal: SocialReuseProposal) -> SocialReuseProposal:
        redacted = SocialReuseProposal.model_validate(
            redact_mapping(proposal.model_dump(mode="json"))
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO social_reuse_proposals (
                  proposal_id, work_item_id, platform, source_revision_id,
                  source_revision_digest, proposal_digest, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(work_item_id, platform, source_revision_id, source_revision_digest)
                DO NOTHING
                """,
                (
                    redacted.proposal_id,
                    redacted.work_item_id,
                    redacted.platform,
                    redacted.source_revision_id,
                    redacted.source_revision_digest,
                    redacted.proposal_digest,
                    redacted.created_at.isoformat(),
                    _model_json(redacted),
                ),
            )
            row = connection.execute(
                """
                SELECT payload_json
                FROM social_reuse_proposals
                WHERE work_item_id = ? AND platform = ?
                  AND source_revision_id = ? AND source_revision_digest = ?
                LIMIT 1
                """,
                (
                    redacted.work_item_id,
                    redacted.platform,
                    redacted.source_revision_id,
                    redacted.source_revision_digest,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("Social reuse proposal was not persisted.")
        return SocialReuseProposal.model_validate(json.loads(cast(str, row["payload_json"])))

    def get_social_reuse_proposal(self, proposal_id: str) -> SocialReuseProposal | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM social_reuse_proposals WHERE proposal_id = ? LIMIT 1",
                (proposal_id,),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    "SELECT payload_json FROM social_reuse_child_proposals "
                    "WHERE proposal_id = ? LIMIT 1",
                    (proposal_id,),
                ).fetchone()
        if row is None:
            return None
        return SocialReuseProposal.model_validate(json.loads(cast(str, row["payload_json"])))

    def list_social_reuse_proposals(
        self,
        work_item_id: str | None = None,
    ) -> list[SocialReuseProposal]:
        with self._connect() as connection:
            if work_item_id is None:
                rows = connection.execute(
                    """
                    SELECT created_at, payload_json FROM social_reuse_proposals
                    UNION ALL
                    SELECT created_at, payload_json FROM social_reuse_child_proposals
                    ORDER BY created_at DESC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT created_at, payload_json FROM social_reuse_proposals
                    WHERE work_item_id = ?
                    UNION ALL
                    SELECT created_at, payload_json FROM social_reuse_child_proposals
                    WHERE work_item_id = ?
                    ORDER BY created_at DESC
                    """,
                    (work_item_id, work_item_id),
                ).fetchall()
        return [
            SocialReuseProposal.model_validate(json.loads(cast(str, row["payload_json"])))
            for row in rows
        ]

    def next_social_reuse_child_number(self, parent_proposal_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(proposal_number), 1) AS current_number
                FROM social_reuse_child_proposals WHERE parent_proposal_id = ?
                """,
                (parent_proposal_id,),
            ).fetchone()
        return int(row["current_number"]) + 1 if row is not None else 2

    def save_social_reuse_child_proposal(
        self,
        proposal: SocialReuseProposal,
    ) -> SocialReuseProposal:
        if proposal.parent_proposal_id is None or proposal.proposal_number < 2:
            raise ValueError("Child social reuse proposal requires a parent and number >= 2.")
        redacted = SocialReuseProposal.model_validate(
            redact_mapping(proposal.model_dump(mode="json"))
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO social_reuse_child_proposals (
                  proposal_id, parent_proposal_id, work_item_id, platform,
                  source_revision_id, source_revision_digest, proposal_digest,
                  proposal_number, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(proposal_id) DO NOTHING
                """,
                (
                    redacted.proposal_id,
                    redacted.parent_proposal_id,
                    redacted.work_item_id,
                    redacted.platform,
                    redacted.source_revision_id,
                    redacted.source_revision_digest,
                    redacted.proposal_digest,
                    redacted.proposal_number,
                    redacted.created_at.isoformat(),
                    _model_json(redacted),
                ),
            )
            row = connection.execute(
                "SELECT payload_json FROM social_reuse_child_proposals "
                "WHERE proposal_id = ? LIMIT 1",
                (redacted.proposal_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError("Child social reuse proposal was not persisted.")
        return SocialReuseProposal.model_validate(json.loads(cast(str, row["payload_json"])))

    def latest_social_reuse_review(self, proposal_id: str) -> SocialReuseReview | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM social_reuse_reviews
                WHERE proposal_id = ? ORDER BY review_number DESC LIMIT 1
                """,
                (proposal_id,),
            ).fetchone()
        if row is None:
            return None
        return SocialReuseReview.model_validate(json.loads(cast(str, row["payload_json"])))

    def save_social_reuse_review(self, review: SocialReuseReview) -> SocialReuseReview:
        redacted = SocialReuseReview.model_validate(
            redact_mapping(review.model_dump(mode="json"))
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO social_reuse_reviews (
                  review_id, proposal_id, proposal_digest, review_number,
                  created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(proposal_id, proposal_digest, review_number) DO NOTHING
                """,
                (
                    redacted.review_id,
                    redacted.proposal_id,
                    redacted.proposal_digest,
                    redacted.review_number,
                    redacted.created_at.isoformat(),
                    _model_json(redacted),
                ),
            )
            row = connection.execute(
                """
                SELECT payload_json FROM social_reuse_reviews
                WHERE proposal_id = ? AND proposal_digest = ? AND review_number = ?
                LIMIT 1
                """,
                (
                    redacted.proposal_id,
                    redacted.proposal_digest,
                    redacted.review_number,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("Social reuse review was not persisted.")
        return SocialReuseReview.model_validate(json.loads(cast(str, row["payload_json"])))
