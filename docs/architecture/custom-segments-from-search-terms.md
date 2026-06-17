# Custom Segments From Search Terms

Pipeline:

1. Pull real search terms from Google Ads.
2. Cluster and clean search terms.
3. Remove irrelevant, low-intent, brand-risk, or duplicated terms.
4. Enrich with Keyword Planner ideas, historical metrics, and forecasts.
5. Build candidate custom segment definitions.
6. Validate segment payload.
7. Create ActionObject.
8. Apply targeting where supported.
9. Log evidence and action history.

The future `wilq-custom-segments` skill must never invent audience terms. It must use WILQ API evidence.

