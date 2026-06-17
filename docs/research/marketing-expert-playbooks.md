# Marketing Expert Playbooks

Machine-readable playbooks live in:

```txt
wilq/knowledge/playbooks/marketing_playbooks.yaml
```

The compiler lives in:

```txt
wilq/knowledge/compilers/playbook_compiler.py
```

Playbook families:

- google_ads_search_playbook
- google_ads_demand_gen_playbook
- google_ads_pmax_playbook
- google_ads_negative_keywords_playbook
- google_ads_custom_segments_playbook
- gsc_seo_content_playbook
- ahrefs_content_gap_playbook
- localo_local_seo_playbook
- ga4_behavior_diagnostics_playbook
- merchant_feed_optimization_playbook
- linkedin_content_playbook
- facebook_content_playbook
- wordpress_content_refresh_playbook

Rules:

- Reference source anchors.
- Declare required evidence.
- Map to opportunity types and action objects.
- Avoid generic marketing advice.
- Keep playbooks machine-readable.

API surface:

- `GET /api/knowledge/playbooks`
- `GET /api/knowledge/playbooks/{playbook_id}`
- `GET /api/knowledge/cards`
- `POST /api/knowledge/condense`

Compiler behavior:

- produces compact `KnowledgeCard` records before Codex context packs,
- preserves `source_type`, `source_id`, `source_url_or_path` and `source_lineage`,
- keeps playbook cards evidence-gated,
- does not produce Ekologus performance claims without connector evidence.
