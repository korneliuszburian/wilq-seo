# Notatki implementacyjne

## Dev: hierarchia nagłówków artykułu

Status: potwierdzony problem motywu `ekologus-2025`; nie jest to problem
semantyki ani generatora WILQ.

Na stronie dev `BDO – co musi wiedzieć przedsiębiorca?` zmierzone style są
odwrócone: tytuł wpisu `.article-header h1` ma `44px`, natomiast
`.article-content h2` ma `56px`. Po prawidłowym usunięciu powielonego H1 z
`post_content` pierwszy H2 artykułu wygląda więc jak główny tytuł.

Nie należy zmieniać HTML wygenerowanego artykułu z H2 na H3. W WordPressie
tytuł wpisu pozostaje jednym H1, a główne sekcje dokumentu pozostają H2.

Minimalna poprawka należy do źródeł motywu (nie do skompilowanego pliku
`/wp-content/themes/ekologus-2025/dist/css/global.css`):

```css
.article-content h2 {
  font-size: var(--text-size-heading-4);
  font-weight: var(--font-bold);
  line-height: 1.2;
}

.article-content h3 {
  font-size: var(--text-size-heading-5);
  font-weight: var(--font-bold);
  line-height: 1.25;
}
```

Efekt: tytuł strony zachowuje wyraźne pierwszeństwo, a H2/H3 tworzą czytelną
hierarchię wewnątrz artykułu. Zmianę trzeba wdrożyć w repozytorium motywu,
zbudować assety i sprawdzić na dev; WILQ nie powinien robić tego przez
zniekształcanie struktury nagłówków w treści.
