# Credential Runtime Bootstrap

Primary local runtime source:

```txt
.env
```

The repo-local `.env` is ignored by git and is the operator convenience layer
for this private WILQ checkout. API processes load it on package import without
overriding already exported shell variables.

Access pack import/fallback source:

```txt
/home/krn/ekologus-access-pack-20260617-120758
/home/krn/ekologus-access-pack-20260617-120758.tar.gz
```

Known contents:

```txt
ekologus.env
README.md
MANIFEST.txt
source-notes/krn-ekologus-superior.env.raw
credentials/gcloud-application_default_credentials.json
credentials/krn-seo-google-ads-oauth-client.json
credentials/seo-command-center-google-ads-oauth-client.json
```

Rules:

- Do not copy secrets into committed files.
- Do not print secret values.
- Keep `.env.example` committed with names only and `.env` untracked.
- Generate connector status from the credential runtime source order:
  `process_env`, `repo_env`, `access_pack_env`, `access_pack_credentials`.
- Access pack remains a bootstrap/fallback source, not the primary API contract.
- Generate `.env.example` from manifest names without values.
- Add redaction before connector logs.

Implementation:

- `wilq/credentials/runtime.py`
- `wilq/access_pack/manifest.py` compatibility shim
- `scripts/access_pack_check.sh`
- `scripts/access_pack_manifest.sh`
