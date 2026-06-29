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

Initial capability definitions:

- `wilq/expert/ads/capabilities.yaml`
- `wilq/expert/ads/demand_gen.yaml`
- `wilq/expert/ads/custom_segments.yaml`
- `wilq/expert/ads/keyword_planner.yaml`
- `wilq/expert/ads/impression_share.yaml`
- `wilq/expert/ads/seasonality.yaml`
- `wilq/expert/ads/scaling_candidates.yaml`
- `wilq/expert/ads/experiments.yaml`
