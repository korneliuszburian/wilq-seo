# Polityki z ekologus-ai - materiał do oceny Wilka

Status: szkic do opinii Wilka. To nie jest zatwierdzona polityka marki,
interpretacja prawna ani wiedza zatwierdzona do finalnych treści.

Data: 2026-07-02

## Po co to pokazujemy

WILQ ma już prywatne, zredagowane propozycje z `ekologus-ai` dla usług
Eko-Opieka i Audyt zgodności. Ten materiał dotyczy drugiej części: polityk,
które mają pilnować jakości twierdzeń w briefach i szkicach.

Sprawdzamy dwie propozycje:

- styl marki i politykę twierdzeń Ekologus;
- bezpieczeństwo prawne, poufność i zgody.

To jest ocena z człowiekiem. Propozycje mogą pomóc w testowaniu i kontroli
jakości, ale nie stają się zatwierdzoną aktualną wiedzą, nie odblokowują
finalnych treści ani publicznych szkiców bez osobnej decyzji o promocji wiedzy.

## Skąd WILQ to bierze

- `ekologus-ai`, zatwierdzone materiały wewnętrzne:
  - `materials_clean/approved/KB_014_STYL_MARKI_JEZYK_EKOLOGUS.cleaned.md`
  - `materials_clean/approved/KB_021_BEZPIECZENSTWO_PRAWNE_POUFNOSC_ZGODY.cleaned.md`
- Fakty źródłowe WILQ:
  - `ekologus_ai_kb014_brand_voice_review_candidate_2026_07_01`
  - `ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01`
- Techniczne akcje Service Profile:
  - `service_profile_review_private_proposal_ekologus_ai_kb014_brand_voice_review_candidate_2026_07_01`
  - `service_profile_review_private_proposal_ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01`

Granica: pokazujemy zredagowane podsumowanie i pola kontroli. Nie pokazujemy
pełnej prywatnej treści, prywatnych przykładów klientów, danych osobowych, kwot,
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

Co może być dozwolone po ocenie:

- treść konkretna, spokojna i ekspercka;
- pokazanie konsekwencji biznesowej i bezpiecznego następnego kroku;
- CTA prowadzące do konsultacji, audytu, monitoringu, szkolenia albo sprzedaży
  bez gwarancji wyniku.

## Jak WILQ rozumie bezpieczeństwo prawne

Kierunek z `ekologus-ai`:

> W materiałach wysokiego ryzyka bezpieczeństwo prawne, poufność, zgody i
> minimalizacja danych mają pierwszeństwo przed sprzedażą.

Co to ma blokować:

- pełną interpretację prawną bez weryfikacji człowieka;
- poufne dane klientów w materiale marketingowym;
- podszywanie automatyzacji pod człowieka;
- gwarantowany wynik administracyjny.

Co może być dozwolone po ocenie:

- wskazanie potrzeby przeglądu eksperckiego zamiast udzielania pełnej
  interpretacji;
- opis procesu i bezpiecznego następnego kroku;
- oznaczenie twierdzeń o karach, kontrolach, urzędach, danych osobowych i
  decyzjach administracyjnych jako wymagających oceny człowieka.

## Pytania do Wilka

1. Czy "konkretnie, spokojnie i ekspercko" dobrze opisuje język Ekologus?
2. Które slogany albo zwroty są zakazane, bo brzmią jak agencja albo generyczne
   SEO?
3. Czy WILQ może blokować straszenie karami, jeżeli tekst nie ma aktualnego
   przeglądu prawnego?
4. Czy twierdzenia o WIOŚ, kontrolach, karach, urzędach i decyzjach mają zawsze
   wymagać oceny człowieka?
5. Czy można publicznie pisać o procesie i bezpiecznym następnym kroku bez
   obiecywania wyniku?
6. Czy te dwie propozycje polityk są gotowe do osobnej decyzji o promocji
   wiedzy, czy wymagają poprawek?
7. Jeśli wymagają poprawek, jakie zadanie follow-up trzeba utworzyć?

## Decyzje do zapisania

W rozmowie użyj normalnych decyzji:

- zatwierdź;
- wróć z poprawkami;
- oznacz jako nieaktualne;
- odrzuć.

Techniczne wartości JSON z live Service Profile to: `approve`,
`needs_changes`, `stale`, `reject`.

Minimalny techniczny wynik oceny dla tych propozycji polityk:

```json
{
  "review_type": "private_source_proposals",
  "data_review": "YYYY-MM-DD",
  "reviewer": "Wilku",
  "scope_label": "prywatne propozycje polityki twierdzeń ekologus-ai",
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
    "wilq-seo-xyz: doprecyzować politykę twierdzeń przed promocją wiedzy"
  ]
}
```

## Sprawdzenie techniczne po rozmowie

Najpierw wygeneruj aktualny JSON wejściowy z live Service Profile, bo pola
oceny są własnością API i mogą się rozszerzać razem z kontraktem:

```bash
rtk uv run python scripts/record_service_profile_review_result.py --print-input-example --review-type private_source_proposals --api-base http://127.0.0.1:8000 > .local-lab/proof/service-profile-policy-review-input-YYYYMMDD.json
```

Po uzupełnieniu decyzji Wilka/ownera sprawdź wynik:

```bash
rtk uv run python scripts/record_service_profile_review_result.py .local-lab/proof/service-profile-policy-review-result-YYYYMMDD.json --api-base http://127.0.0.1:8000 --format markdown
```

Potem sprawdź, czy wynik oceny jest w ogóle gotowy do osobnej promocji wiedzy:

```bash
rtk uv run python scripts/record_service_profile_review_result.py .local-lab/proof/service-profile-policy-review-result-YYYYMMDD.json --api-base http://127.0.0.1:8000 --promotion-readiness --format markdown
```

To nadal nie promuje prywatnej propozycji do faktu źródłowego. Obecny stan
powinien blokować gotowość promocji, jeżeli brakuje `evidence_ids` albo decyzja
retencji nadal jest `pending_owner_decision`.

## Czego ta ocena nie robi

- Nie promuje prywatnej propozycji do faktu źródłowego.
- Nie kompiluje zatwierdzonej aktualnej karty wiedzy.
- Nie odblokowuje wiedzy do finalnych treści.
- Nie odblokowuje publicznych szkiców ani WordPress.
- Nie pozwala WILQ udzielać interpretacji prawnej bez człowieka.

## Co WILQ powinien zrobić po opinii

Jeżeli Wilku zatwierdzi oba kierunki:

- przygotować osobny, audytowany wniosek o promocję prywatnego źródła;
- dopiero po tej promocji używać polityk jako bramek w Claim Ledger i kontroli
  jakości;
- nadal blokować prawne i wysokiego ryzyka twierdzenia bez oceny człowieka.

Jeżeli Wilku wybierze "wróć z poprawkami":

- zapisać zadanie follow-up;
- nie promować propozycji polityk;
- poprawić fakty źródłowe albo opis do oceny przed kolejną próbą.

Jeżeli Wilku odrzuci albo oznaczy jako nieaktualne:

- oznaczyć propozycję jako odrzuconą albo nieaktualną w przyszłej ścieżce oceny;
- nie używać tej polityki jako bramki jakości;
- usunąć albo zostawić zredagowany artefakt tylko jako historyczną notatkę z
  oceny.
