# Access Pack Bootstrap

Known access pack:

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
- Read only variable names and credential file availability.
- Generate connector status from env/key presence.
- Generate `.env.example` from manifest names without values.
- Add redaction before connector logs.

Implementation:

- `wilq/access_pack/manifest.py`
- `scripts/access_pack_check.sh`
- `scripts/access_pack_manifest.sh`

