from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Action = Literal["blocked", "keep", "noindex", "redirect"]
Confidence = Literal["high", "medium", "low"]
Status = Literal["blocked", "resolved"]
SelectedAuthority = Literal["strategy", "tie_breaker"]
ConfidenceAuthority = Literal["integrator_decision_packet", "tie_breaker"]
AuthorityName = Literal["ledger", "journal"]
JsonPathPart = str | int
ReceiptDetector = Literal["hex64", "hex40", "base64"]
CaveatStatus = Literal["active", "superseded"]
CaveatDisposition = Literal["applies", "corrected_by_canonical_sitemap_inventory"]


@dataclass(frozen=True)
class SourceArtifact:
    role: str
    artifact_reference: str
    content: bytes
    expected_sha256: str


@dataclass(frozen=True)
class JudgeReceipt:
    role: str
    artifact_reference: str
    sha256: str
    algorithm: str = "sha256_file_bytes_v1"

    def as_json(self) -> dict[str, str]:
        return {
            "role": self.role,
            "artifact_reference": self.artifact_reference,
            "sha256": self.sha256,
            "algorithm": self.algorithm,
        }


@dataclass(frozen=True)
class CaveatCorrection:
    statement_pl: str
    source_reference: str
    source_sha256: str
    evidence_ids: tuple[str, ...]
    observed_entry_count: int
    unique_path_count: int
    duplicate_path: str
    duplicate_sitemaps: tuple[str, str]

    def as_json(self) -> dict[str, object]:
        return {
            "statement_pl": self.statement_pl,
            "source_reference": self.source_reference,
            "source_sha256": self.source_sha256,
            "evidence_ids": list(self.evidence_ids),
            "observed_entry_count": self.observed_entry_count,
            "unique_path_count": self.unique_path_count,
            "duplicate_path": self.duplicate_path,
            "duplicate_sitemaps": list(self.duplicate_sitemaps),
        }


@dataclass(frozen=True)
class EvidenceCaveat:
    caveat_id: str
    source_role: str
    artifact_reference: str
    source_path: str
    text: str
    evidence_ids: tuple[str, ...]
    status: CaveatStatus
    disposition: CaveatDisposition
    correction: CaveatCorrection | None

    def as_json(self) -> dict[str, object]:
        return {
            "caveat_id": self.caveat_id,
            "source_role": self.source_role,
            "artifact_reference": self.artifact_reference,
            "source_path": self.source_path,
            "text": self.text,
            "evidence_ids": list(self.evidence_ids),
            "status": self.status,
            "disposition": self.disposition,
            "correction": self.correction.as_json() if self.correction is not None else None,
        }


@dataclass(frozen=True)
class JudgeRowLineage:
    url: str
    technical_row_digest: str
    strategy_row_digest: str
    tie_breaker_row_digest: str | None
    selected_authority: SelectedAuthority
    confidence_authority: ConfidenceAuthority


@dataclass(frozen=True)
class JudgeLineage:
    receipts: tuple[JudgeReceipt, ...]
    receipt_set_digest: str
    caveats: tuple[EvidenceCaveat, ...]
    caveat_set_digest: str
    rows: tuple[JudgeRowLineage, ...]

    @property
    def rows_by_url(self) -> dict[str, JudgeRowLineage]:
        return {row.url: row for row in self.rows}


@dataclass(frozen=True)
class AdjudicationProvenance:
    recorded_at: str
    base_revision: str
    baseline_semantics: str
    raw_judge_artifacts_retained: bool
    raw_judge_retention_status: str

    def as_json(self) -> dict[str, str | bool]:
        return {
            "recorded_at": self.recorded_at,
            "base_revision": self.base_revision,
            "baseline_semantics": self.baseline_semantics,
            "raw_judge_artifacts_retained": self.raw_judge_artifacts_retained,
            "raw_judge_retention_status": self.raw_judge_retention_status,
        }


@dataclass(frozen=True)
class NoindexAdjudicationSources:
    integrated_decision: SourceArtifact
    technical_judge: SourceArtifact
    strategy_judge: SourceArtifact
    tie_breaker_judge: SourceArtifact
    ledger: SourceArtifact
    journal: SourceArtifact
    recorded_at: str
    base_revision: str

    @property
    def judge_artifacts(self) -> tuple[SourceArtifact, SourceArtifact, SourceArtifact]:
        return (self.technical_judge, self.strategy_judge, self.tie_breaker_judge)

    @property
    def provenance(self) -> AdjudicationProvenance:
        return AdjudicationProvenance(
            recorded_at=self.recorded_at,
            base_revision=self.base_revision,
            baseline_semantics=(
                "additive_re_adjudication_over_older_operational_baseline_without_refreshing_"
                "top_level_state"
            ),
            raw_judge_artifacts_retained=False,
            raw_judge_retention_status=(
                "external_ephemeral_judge_files_not_retained_receipts_only"
            ),
        )


@dataclass(frozen=True)
class ProductionPins:
    input_receipt_sha256: str
    judge_receipts: tuple[JudgeReceipt, ...]
    judge_receipt_set_digest: str
    decision_set_digest: str | None
    caveat_set_digest: str | None
    ledger_baseline_digest: str
    journal_baseline_digest: str
    provenance: AdjudicationProvenance


@dataclass(frozen=True)
class AdjudicationExpectations:
    ledger_rows: int = 214
    operational_counts: tuple[tuple[str, int], ...] = (
        ("keep", 57),
        ("noindex", 87),
        ("redirect", 46),
        ("remove", 24),
    )
    decision_rows: int = 87
    recommendation_counts: tuple[tuple[str, int], ...] = (
        ("blocked", 9),
        ("keep", 25),
        ("noindex", 17),
        ("redirect", 36),
        ("remove", 0),
    )
    resolved_rows: int = 78
    blocked_rows: int = 9
    production_pins: ProductionPins | None = None

    @property
    def operational_partition(self) -> dict[str, int]:
        return dict(self.operational_counts)

    @property
    def recommendation_partition(self) -> dict[str, int]:
        return dict(self.recommendation_counts)


@dataclass(frozen=True)
class AdjudicationDecision:
    path: str
    source_url: str
    source_public_url: str
    recommended_action: Action
    recommended_target_url: str | None
    status: Status
    confidence: Confidence
    decision_basis_pl: str
    evidence_ids: tuple[str, ...]
    blockers: tuple[str, ...]
    decision_receipt_sha256: str
    input_receipt_sha256: str
    judge_receipt_set_digest: str
    caveat_set_digest: str
    technical_row_digest: str
    strategy_row_digest: str
    tie_breaker_row_digest: str | None
    selected_authority: SelectedAuthority
    confidence_authority: ConfidenceAuthority
    input_reference: str


@dataclass(frozen=True)
class ReconciliationResult:
    ledger_bytes: bytes
    journal_bytes: bytes
    input_receipt_sha256: str
    decision_set_digest: str
    caveat_set_digest: str


@dataclass(frozen=True)
class RetainedReceiptOccurrence:
    authority: AuthorityName
    path: tuple[JsonPathPart, ...]
    value: str
    detector: ReceiptDetector


@dataclass(frozen=True)
class RetainedAuthorities:
    receipt_occurrences: tuple[RetainedReceiptOccurrence, ...]
    decision_set_digest: str
    caveat_set_digest: str
