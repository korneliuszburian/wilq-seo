# Google Ads Capability Pack

WILQ represents BDOS-class Google Ads workflows as WILQ API capabilities, not loose commands.

Every Ads capability maps to required connector inputs, evidence, metrics, diagnosis logic, action object types, risk, write capability, API limitations, and validation checks.

## API version intake

WILQ uses the Google Ads major REST endpoint (`v24`) for the current connector.
Google Ads minor releases such as `v24.2` automatically update the existing
major endpoint; they do not require changing the endpoint string to `v24.2` or
`v24_2`.

When a minor release adds useful capabilities, add them as explicit WILQ read or
review contracts:

- confirm the official release note and field/resource docs;
- add the GAQL/read contract and blocked-state behavior;
- add schema/API/dashboard/skill proof only for the capability being exposed;
- keep write/apply blocked until WILQ has preview, confirmation, audit and
  measurement coverage.

## GAQL and read-adapter guardrails

WILQ should copy the official Google Ads developer-toolkit pattern instead of
letting skills invent GAQL in prose:

- Query Builder pattern: every repeated Ads workflow should have an explicit
  query contract with resource, selected fields, segments, filters, ordering and
  limits.
- Query Validator pattern: generated or edited GAQL must pass compatibility
  checks before a live read. The check should catch syntax, missing SELECT
  fields required by WHERE/ORDER BY, incompatible metrics/segments and wrong
  resource models.
- API Explorer pattern: new read contracts may be prototyped against live
  Google Ads response shape, but only sanitized aggregates, evidence IDs,
  source connectors and blocked-state labels are persisted by WILQ.
- MCP server pattern: account discovery, GAQL search and resource metadata can
  be adapter tools, but MCP output is not a recommendation until WILQ stores it
  as redacted refresh/evidence state.

Keyword Planner remains a separate readiness contract. If Google returns
`DEVELOPER_TOKEN_NOT_APPROVED`, WILQ must expose developer-token approval as
the blocker rather than falling back to invented volume, CPC or forecast data.

Initial capability definitions:

- `wilq/expert/ads/capabilities.yaml`
- `wilq/expert/ads/demand_gen.yaml`
- `wilq/expert/ads/custom_segments.yaml`
- `wilq/expert/ads/keyword_planner.yaml`
- `wilq/expert/ads/impression_share.yaml`
- `wilq/expert/ads/seasonality.yaml`
- `wilq/expert/ads/scaling_candidates.yaml`
- `wilq/expert/ads/experiments.yaml`
