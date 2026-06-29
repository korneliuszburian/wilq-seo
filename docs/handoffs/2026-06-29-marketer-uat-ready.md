# Marketer UAT Ready - 2026-06-29

Status: ready for real marketer session, not completed UAT.

## What Is Ready

- Local WILQ API and dashboard were reachable when the packet was generated.
- The live UAT packet exporter reads current WILQ API surfaces for:
  - Centrum pracy
  - Merchant
  - Treści
  - Google Ads
  - GA4
- The packet uses Polish operator-facing snapshot fields and avoids raw route,
  decision-type, status and URL-contract keys in the visible WILQ preview.
- The result recorder accepts the same Polish filled-result shape.

## Generate Current Packet

Run from repo root:

```bash
rtk uv run python scripts/export_marketer_uat_packet.py \
  --api-base http://127.0.0.1:8000 \
  --format markdown > .local-lab/proof/marketer-uat-packet-$(date +%Y%m%d).md

rtk uv run python scripts/export_marketer_uat_packet.py \
  --api-base http://127.0.0.1:8000 \
  --format json > .local-lab/proof/marketer-uat-packet-$(date +%Y%m%d).json
```

The generated packet is ignored under `.local-lab/`; it is live proof material,
not a committed source document.

## Run The Session

Open:

```text
http://127.0.0.1:5173/command-center
```

Give Wilku or the marketer 15 minutes. Do not explain statuses first. The
person should answer from the UI:

1. What is the next action?
2. Which screen gives the biggest real value?
3. Where did they need to guess what a field/status means?
4. Does Treści save time deciding what to keep, refresh or merge on
   `ekologus.pl`?
5. How much time does this save: 0, 15, 30 or 60+ minutes?

## Record Result

Save a filled JSON file under `.local-lab/proof/`, for example:

```json
{
  "data": "2026-06-29",
  "osoba": "Wilku",
  "centrum_pracy": "zaliczone <notatka>",
  "merchant": "zaliczone <notatka>",
  "treści": "zaliczone <notatka>",
  "google_ads": "zaliczone <notatka>",
  "ga4": "zaliczone <notatka>",
  "największy_realny_zysk": "<opis>",
  "największa_niejasność": "<opis>",
  "nowe_zadania": ["<zadanie z feedbacku>"],
  "gotowe_bez_developera": "tak"
}
```

Then run:

```bash
rtk uv run python scripts/record_marketer_uat_result.py \
  .local-lab/proof/marketer-uat-result-20260629.json \
  --format markdown > .local-lab/proof/marketer-uat-result-20260629.md
```

## Check Completion Proof

Before claiming Goal 001 completion, run the guard:

```bash
rtk uv run python scripts/goal_001_completion_check.py \
  --uat-result .local-lab/proof/marketer-uat-result-20260629.json \
  --format markdown
```

If the owner explicitly defers real UAT instead of running the session, save a
JSON note under `.local-lab/proof/`, for example:

```json
{
  "odroczenie_realnego_uat": true,
  "data": "2026-06-29",
  "osoba": "<owner>",
  "powód": "<dlaczego UAT jest odroczony>",
  "co_można_pokazać": "<bezpieczny zakres demo>",
  "zablokowane_obietnice": [
    "potwierdzona użyteczność marketera",
    "gotowość bez developera"
  ]
}
```

Then run:

```bash
rtk uv run python scripts/goal_001_completion_check.py \
  --owner-defer .local-lab/proof/marketer-uat-owner-defer-20260629.json \
  --format markdown
```

## Completion Rule

Goal 001 can only claim UAT completion when one of these is true:

- A filled real marketer UAT result exists and `record_marketer_uat_result.py`
  validates it.
- The owner explicitly defers real marketer UAT and the defer note states:
  - who deferred,
  - date,
  - reason,
  - what remains safe to show,
  - what product claims stay blocked.

Until then, WILQ has a verified cleanup gate and a ready UAT packet, not a
completed usefulness proof.
