"""Dispatch validated ActionObjects to local or WordPress mutation adapters."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.actions.local_content_mutation_adapters import (
    execute_local_content_mutation_adapter,
    is_local_content_mutation_adapter,
)
from wilq.actions.wordpress_mutation_requirements import (
    execute_supported_wordpress_mutation_adapter,
)
from wilq.audit.trusted_local_confirmation import TrustedLocalPrincipalReceipt
from wilq.content.workflow.research_packet_current import CurrentSnapshotLoader
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import ActionObject
from wilq.storage.local_state import LocalStateStore


def execute_supported_mutation_adapter(
    action: ActionObject,
    mutation_adapter: str,
    wordpress_capability: Any = None,
    *,
    workflow_store: ContentWorkflowStore,
    audit_store_factory: Callable[[], LocalStateStore],
    trusted_principal_receipt: TrustedLocalPrincipalReceipt | None = None,
    content_snapshot_loader: CurrentSnapshotLoader | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    if is_local_content_mutation_adapter(mutation_adapter):
        local_result = execute_local_content_mutation_adapter(
            action,
            mutation_adapter,
            workflow_store=workflow_store,
            audit_store_factory=audit_store_factory,
            trusted_principal_receipt=trusted_principal_receipt,
            content_snapshot_loader=content_snapshot_loader,
        )
        if local_result is None:
            return None, ["Nieznany lokalny adapter treści."]
        return local_result
    return execute_supported_wordpress_mutation_adapter(
        action, mutation_adapter, wordpress_capability
    )


__all__ = ["execute_supported_mutation_adapter"]
