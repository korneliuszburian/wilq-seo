# Ekologus-ai policy proposals - materiał do review Wilka

Status: szkic do opinii Wilka. To nie jest zatwierdzona polityka marki,
interpretacja prawna ani production-depth knowledge.

Data: 2026-07-02

## Po co to pokazujemy

WILQ ma już prywatne, redacted propozycje z `ekologus-ai` dla usług
Eko-Opieka i Audyt zgodności. Ten materiał dotyczy drugiej części: polityk,
które mają pilnować jakości claimów w briefach i draftach.

Sprawdzamy dwie propozycje:

- styl marki i claim policy Ekologus;
- bezpieczeństwo prawne, poufność i zgody.

To jest review z człowiekiem. Propozycje mogą pomóc w UAT i quality review, ale
nie odblokowują `approved_current`, production-depth ani publicznych draftów bez
osobnego review/promotion request.

## Skąd WILQ to bierze

- `ekologus-ai`, zatwierdzone materiały wewnętrzne:
  - `materials_clean/approved/KB_014_STYL_MARKI_JEZYK_EKOLOGUS.cleaned.md`
  - `materials_clean/approved/KB_021_BEZPIECZENSTWO_PRAWNE_POUFNOSC_ZGODY.cleaned.md`
- WILQ source facts:
  - `ekologus_ai_kb014_brand_voice_review_candidate_2026_07_01`
  - `ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01`
- Live Service Profile action IDs:
  - `service_profile_review_private_proposal_ekologus_ai_kb014_brand_voice_review_candidate_2026_07_01`
  - `service_profile_review_private_proposal_ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01`

Granica: pokazujemy redacted summary i governance fields. Nie pokazujemy raw
private content, prywatnych przykładów klientów, danych osobowych, kwot,
transkrypcji ani niezatwierdzonych interpretacji prawnych.

## Jak WILQ rozumie styl marki

Kierunek z `ekologus-ai`:

> Ekologus powinien mówić konkretnie, spokojnie i ekspercko. Bez pustych
> sloganów agencyjnych, bez straszenia dla samego straszenia i bez obietnic
> gwarantowanego wyniku.

Co to ma blokować:

- puste slogany agencyjne;
- gwarantowany wynik;
- straszenie bez powodu;
- pełną interpretację prawną w darmowej treści.

Co może być dozwolone po review:

- treść konkretna, spokojna i ekspercka;
- pokazanie konsekwencji biznesowej i bezpiecznego następnego kroku;
- CTA prowadzące do konsultacji, audytu, monitoringu, szkolenia albo sprzedaży
  bez gwarancji wyniku.

## Jak WILQ rozumie legal-safety

Kierunek z `ekologus-ai`:

> W materiałach wysokiego ryzyka bezpieczeństwo prawne, poufność, zgody i
> minimalizacja danych mają pierwszeństwo przed sprzedażą.

Co to ma blokować:

- pełną interpretację prawną bez weryfikacji człowieka;
- poufne dane klientów w materiale marketingowym;
- podszywanie automatyzacji pod człowieka;
- gwarantowany wynik administracyjny.

Co może być dozwolone po review:

- wskazanie potrzeby przeglądu eksperckiego zamiast udzielania pełnej
  interpretacji;
- opis procesu i bezpiecznego następnego kroku;
- oznaczenie claimów o karach, kontrolach, urzędach, danych osobowych i
  decyzjach administracyjnych jako human-review gated.

## Pytania do Wilka

1. Czy "konkretnie, spokojnie i ekspercko" dobrze opisuje język Ekologus?
2. Które slogany albo zwroty są zakazane, bo brzmią jak agencja albo generic
   SEO?
3. Czy WILQ może blokować straszenie karami, jeżeli tekst nie ma aktualnego
   review prawnego?
4. Czy claimy o WIOŚ, kontrolach, karach, urzędach i decyzjach mają zawsze
   wymagać human review?
5. Czy można publicznie pisać o procesie i bezpiecznym następnym kroku bez
   obiecywania wyniku?
6. Czy te dwie policy proposals są gotowe do osobnego promotion request, czy
   wymagają poprawek?
7. Jeśli wymagają poprawek, jakie follow-up Beads trzeba utworzyć?

## Decyzje do zapisania

Użyj decision options z live Service Profile:

- `approve`
- `needs_changes`
- `stale`
- `reject`

Minimalny wynik review dla tych policy proposals:

```json
{
  "review_type": "private_source_proposals",
  "data_review": "YYYY-MM-DD",
  "reviewer": "Wilku",
  "scope_label": "prywatne claim-policy proposals ekologus-ai",
  "decisions": [
    {
      "action_id": "service_profile_review_private_proposal_ekologus_ai_kb014_brand_voice_review_candidate_2026_07_01",
      "target_card_id": "ekologus_claim_policy_brand_voice",
      "decision": "needs_changes",
      "source_trace_clear": "tak",
      "blocked_claims_reviewed": "tak",
      "data_classes_confirmed": "tak",
      "source_block_refs_confirmed": "tak",
      "freshness_status_confirmed": "tak",
      "audience_scope_confirmed": "tak",
      "retention_decision_confirmed": "tak",
      "deletion_path_confirmed": "tak",
      "eval_gates_confirmed": "tak",
      "notes": "co Wilku zatwierdza albo co wymaga zmiany"
    },
    {
      "action_id": "service_profile_review_private_proposal_ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01",
      "target_card_id": "ekologus_claim_policy_legal_safety",
      "decision": "needs_changes",
      "source_trace_clear": "tak",
      "blocked_claims_reviewed": "tak",
      "data_classes_confirmed": "tak",
      "source_block_refs_confirmed": "tak",
      "freshness_status_confirmed": "tak",
      "audience_scope_confirmed": "tak",
      "retention_decision_confirmed": "tak",
      "deletion_path_confirmed": "tak",
      "eval_gates_confirmed": "tak",
      "notes": "co Wilku zatwierdza albo co wymaga zmiany"
    }
  ],
  "follow_up_beads": [
    "wilq-seo-xyz: doprecyzować claim policy przed promotion request"
  ]
}
```

Sprawdzenie wyniku:

Najpierw wygeneruj aktualny JSON wejściowy z live Service Profile, bo pola
review są własnością API i mogą się rozszerzać razem z kontraktem:

```bash
rtk uv run python scripts/record_service_profile_review_result.py --print-input-example --review-type private_source_proposals --api-base http://127.0.0.1:8000 > .local-lab/proof/service-profile-policy-review-input-YYYYMMDD.json
```

Po uzupełnieniu decyzji Wilka/ownera sprawdź wynik:

```bash
rtk uv run python scripts/record_service_profile_review_result.py .local-lab/proof/service-profile-policy-review-result-YYYYMMDD.json --api-base http://127.0.0.1:8000 --format markdown
```

## Czego ten review nie robi

- Nie promuje private proposal do source fact.
- Nie kompiluje `approved_current` knowledge card.
- Nie odblokowuje production-depth.
- Nie odblokowuje draftów publicznych ani WordPress.
- Nie pozwala WILQ udzielać interpretacji prawnej bez człowieka.

## Co WILQ powinien zrobić po opinii

Jeżeli Wilku zatwierdzi oba kierunki:

- przygotować osobny, audytowany private source promotion request;
- po promotion request dopiero używać polityk jako gates w Claim Ledger i
  quality review;
- nadal blokować legal/high-risk claimy bez human review.

Jeżeli Wilku oznaczy `needs_changes`:

- zapisać follow-up Beads;
- nie promować policy proposals;
- poprawić source facts albo review copy przed kolejną próbą.

Jeżeli Wilku odrzuci:

- oznaczyć proposal jako rejected/stale w przyszłej ścieżce review;
- nie używać tej polityki jako quality gate;
- usunąć albo zostawić redacted artifact tylko jako historical review note.
