# Content Quality Standards — research decyzyjny dla pipeline'u treści WILQ

Rola dokumentu: `decision` — wynik source-to-decision dla standardów jakości treści.
Nie opisuje bieżącego stanu produktu; decyzje adopt/reject/lab-test wymagają
slice'ów z falsifierami (ścieżka: docs/agents/reports/benchmark/ + beads).

## Decision question

- Pytanie: które zewnętrzne standardy jakości treści WILQ ma adoptować w pipeline
  (planning → draft → gates), a które odrzucić lub przetestować?
- Aktywny konsument: Goal „5 luk prod-ready" — punkty 1/3/5 (research, jakość
  merytoryczna, benchmark).
- Obecne zachowanie: pipeline ma deterministyczne bramki (working_note,
  duplicate_paragraph, thin_section, wall_of_text), LLM semantic review (9
  wymiarów), regulatory assurance — ale brak byline/author, brak disclosure
  automatyzacji, brak progu długości zdania, brak jawnych sygnałów E-E-A-T
  reader-facing.
- Non-proof boundary: nie decydujemy o wyniku rankingowym Google (żadne źródło
  tego nie obiecuje); nie wprowadzamy „score'u E-E-A-T" (Google wprost mówi,
  że E-E-A-T nie jest rankingowym czynnikiem liczbowym).

## Źródła

| # | Źródło | Wersja/data | Zakres autorytetu |
|---|---|---|---|
| S1 | Google Search Central — Creating helpful, reliable, people-first content | 2025-12-10 | mechanika: co Google nagradza (people-first), samoaudyt content |
| S2 | Google Search Central blog — Google Search's guidance about AI-generated content | 2023-02-08 | mechanika: AI content nie jest sam w sobie spamem; disclosure; scaled content abuse |
| S3 | NN/g — Plain Language Is for Everyone, Even Experts (Loranger) | 2017-10-08 | mechanika: czytelność (zdania 15–20 słów, akapity 1–2 zdania, poziom 6–8/10–12 klasy, nagłówki, inverted pyramid) |
| S4 | NN/g — The 3-Step CTAs Formula for Conversion (Dykes) | video, 2024 | mechanika: CTA (jedno główne działanie, konkretny czasownik, brak słabych CTA) |
| S5 | Google Search Central — Understanding E-E-A-T (osadzone w S1 + rater guidelines) | 2025 | mechanika: trust > expertise; YMYL wyższa poprzeczka |

## Mechanism extraction

### S1 — People-first

- Stated claim: content created primarily for people (nie dla rankingu) jest
  nagradzane; samoaudyt pyta: oryginalna wartość? kompletny opis? insightful
  analysis? heading descriptive, nie exaggerating? „czy tę stronę byś
  bookmarkował/polecił?"
- Transferable mechanism: heading/title = descriptive summary (nie clickbait);
  treść = substantial, complete, beyond obvious; unikalność vs inne strony w
  wynikach; brak stylistycznych błędów.
- Conditions/limitations: to nie checklista rankingowa, tylko samoocena;
  „automation is not inherently spam" — liczy się jakość i cel.
- Local evidence: `wilq/codex/prompts.py` content_initial_draft@v2 wymaga
  „Używaj pól target_reader... aby ustalić, do kogo piszesz", „Każdy nagłówek
  sekcji ma nazywać konkretną odpowiedź" — heading-as-promise już w prompt.
  Brak: gate na title/heading exaggeration, brak byline (Who), brak disclosure
  (How).
- Inference: pipeline częściowo pokrywa people-first przez prompt, ale nie ma
  deterministycznego gate na „heading descriptive/nie exaggerating".

### S2 — AI content

- Stated claim: AI-generated content nie jest spamem per se; spam to scaled
  content abuse (masowa produkcja bez wartości); disclosure przydatny gdzie
  czytelnik może się spodziewać pytania „how was this made".
- Transferable mechanism: jawność procesu (How) buduje trust; masowość bez
  wartości = ryzyko.
- Local evidence: brak jakiegokolwiek pola author/disclosure w
  `wilq/content/drafts/initial_full_draft_contracts.py`
  (ContentDraftRevisionPageAssets: wordpress_title, meta_title,
  meta_description, h1, lead — bez byline) ani w dashboard.
- Inference: WILQ powinno móc renderować „proces: plan z dowodów + review" —
  ale to jest decyzja product-facing, nie rankingowa.

### S3 — Plain language (NN/g)

- Stated claim: zdania 15–20 słów; akapity 1–2 zdania; poziom 6–8 (ogół) /
  10–12 (eksperci); nagłówki informacyjne; inverted pyramid; scanability.
- Transferable mechanism: długość zdania jest mierzalna deterministycznie.
- Local evidence: `wilq/content/quality/reading_quality.py` ma wall_of_text
  (akapit > 220 słów) i thin_section (< 12 słów) — ale **brak progu długości
  zdania** (15–20 słów) i brak liczby zdań na akapit.
- Inference: dodać sentence-length gate jako deterministyczną bramkę pre-save
  (analogicznie do wall_of_text).

### S4 — CTA

- Stated claim: silne CTA = konkretny czasownik + jedna główna akcja; słabe CTA
  („kliknij tutaj", „skontaktuj się") obniżają konwersję.
- Local evidence: `wilq/content/quality/reading_quality.py:107 weak_cta()`
  istnieje i jest używane w review_findings; `minimum_cta_blocks` i
  `required_cta_patterns` w planning (dynamic_input.py:147-148) wymuszają
  liczbę CTA.
- Inference: CTA już pokryte (weak_cta + min blocks) — brak nowego gate.

### S5 — E-E-A-T / YMYL

- Stated claim: trust najważniejszy; YMYL (finanse/zdrowie/bezpieczeństwo)
  wymaga wyższej poprzeczki dowodów; byline/author info buduje Who.
- Local evidence: `wilq/content/knowledge/service_profile/` ma regulatory
  profile (official_source facts, approved claims) — YMYL dla BDO jest już
  obsłużone przez regulatory assurance. Brak: byline/author reader-facing.
- Inference: YMYL pokryty architektonicznie (regulatory), brakuje tylko
  reader-facing Who/How (jeśli Wilku chce).

## Decyzje (source-to-decision)

| Standard | Decyzja | Uzasadnienie | Falsifier/eksperyment |
|---|---|---|---|
| S1 heading descriptive (nie exaggerating) | **adopt** | prompt mówi, gate nie pilnuje; tani regex/LLM-check | falsifier: heading z „najlepszy/największy" bez źródła → blocker |
| S1 byline/author (Who) | **lab-test** | wymaga decyzji produktowej (czy Ekologus chce byline); wpływa na kontrakt page_assets | eksperyment: dodać pole author do page_assets + render w pakiecie |
| S2 automation disclosure (How) | **defer** | disclosure to decyzja Wilku/marketera, nie bramka jakości; pipeline ma już lineage wewnętrznie | brak konsumenta dziś — defer z powodem |
| S3 sentence-length gate | **adopt** | deterministyczny, tani, zgodny z NN/g; domyka wall_of_text | falsifier: zdanie > 20 słów → issue sentence_length |
| S3 reading level | **defer** | polskie stopnie czytelności nie mają prostego odpowiednika Flescha; ryzyko false positives | brak sprawdzonej polskiej miary — defer |
| S4 CTA | **adopt (już wdrożone)** | weak_cta + min blocks już istnieją | testy już istnieją (weak_cta) |
| S5 YMYL | **adopt (już wdrożone)** | regulatory assurance + official_source facts | testy regulatory już istnieją |

## Luki pipeline'u (konkretne)

1. **Brak progu długości zdania** — `wilq/content/quality/reading_quality.py`
   (wall_of_text 220 słów/akapit, ale zero check na zdanie 15–20 słów).
   Severity: medium. Adopt (S3).
2. **Brak gate na exaggerating heading/title** — prompt mówi „nagłówek jest
   obietnicą", brak deterministycznej kontroli (np. superlatywy bez źródła).
   Severity: low-medium. Adopt (S1).
3. **Brak byline/author w kontrakcie page_assets** —
   `initial_full_draft_contracts.py` ContentDraftRevisionPageAssets (5 pól,
   zero author). Severity: low (product decision). Lab-test (S1/S5).
4. **Brak automation disclosure** — zero pola How/process reader-facing.
   Severity: low. Defer (S2) — decyzja Wilku.
5. **Brak polskiej miary czytelności** — reading level nie mierzony.
   Severity: low. Defer (S3) — brak sprawdzonej miary dla pl-PL.

## Plan slice'ów (kolejność)

1. Q31: sentence-length gate w reading_quality.py (adopt S3) + falsifier.
2. Q32: heading-exaggeration gate (adopt S1) + falsifier.
3. Q33: byline w page_assets (lab-test S1) — rozszerzenie kontraktu + render.
4. Q34: benchmark przed/po (punkt 5 celu) — deterministyczne metryki per strona.
5. Q35: measurement window realne GSC/GA4 (punkt 2 celu).

## Does not prove

- Żaden z adoptów nie obiecuje rankingowego wyniku Google.
- „9/9 semantic review" nie jest dowodem użyteczności dla czytelnika — wymaga
  benchmarku przed/po (Q34) i realnych metryk (Q35).
- E-E-A-T nie jest scorem; byline to sygnał zaufania, nie gwarancja rankingu.
