# Retrieval And Knowledge Patterns

WILQ uses knowledge cards rather than giant prompt dumps.

Source anchors:

- RAG: external non-parametric memory improves factuality and updateability.
- Lost in the Middle: long context may underuse information placed in the middle.
- Self-RAG: retrieval and critique patterns improve controllability.
- RAGAS: retrieval and generation quality can be evaluated with relevance, faithfulness, context precision and answer quality.

Product decisions:

- Condense source material into knowledge cards.
- Preserve source lineage.
- Retrieve compact context packs for Codex.
- Do not make vector DB a Goal 001 dependency.

