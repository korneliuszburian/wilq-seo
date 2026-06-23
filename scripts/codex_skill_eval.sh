#!/usr/bin/env bash
set -euo pipefail

api_base="${WILQ_API_BASE:-http://127.0.0.1:8000}"
cases_file="docs/evals/cases/wilq-skill-eval-cases.json"
schema_file="docs/evals/schemas/wilq-skill-eval-result.schema.json"
requested_skill=""
sandbox="${CODEX_SKILL_EVAL_SANDBOX:-workspace-write}"
ephemeral="${CODEX_SKILL_EVAL_EPHEMERAL:-1}"
out_root="${CODEX_SKILL_EVAL_OUT:-.local-lab/evals/codex-skill/$(date -u +%Y%m%dT%H%M%SZ)}"
timeout_s="${CODEX_SKILL_EVAL_TIMEOUT:-300}"
network_access="${CODEX_SKILL_EVAL_NETWORK_ACCESS:-true}"
ignore_user_config="${CODEX_SKILL_EVAL_IGNORE_USER_CONFIG:-0}"

usage() {
  cat <<'EOF'
Usage:
  scripts/codex_skill_eval.sh --all [--api-base URL]
  scripts/codex_skill_eval.sh --skill wilq-daily-command [--api-base URL]

Environment:
  WILQ_API_BASE                 Default API base URL.
  CODEX_SKILL_EVAL_SANDBOX      Codex sandbox, default workspace-write.
  CODEX_SKILL_EVAL_EPHEMERAL    1 to pass --ephemeral, default 1.
  CODEX_SKILL_EVAL_TIMEOUT      Timeout per skill in seconds, default 300.
  CODEX_SKILL_EVAL_NETWORK_ACCESS
                                  true to allow localhost/API access in workspace-write, default true.
  CODEX_SKILL_EVAL_IGNORE_USER_CONFIG
                                  1 to pass --ignore-user-config, default 0.
  CODEX_SKILL_EVAL_OUT          Output directory, default .local-lab/evals/codex-skill/<utc>.
EOF
}

if [ "$#" -eq 0 ]; then
  usage
  exit 2
fi

while [ "$#" -gt 0 ]; do
  case "$1" in
    --all)
      requested_skill="__all__"
      shift
      ;;
    --skill)
      requested_skill="${2:-}"
      shift 2
      ;;
    --api-base)
      api_base="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$requested_skill" ]; then
  echo "Pass --all or --skill <name>." >&2
  exit 2
fi

command -v codex >/dev/null 2>&1 || {
  echo "codex command not found." >&2
  exit 127
}

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if ! curl -fsS --max-time 2 "$api_base/api/health" >/dev/null; then
  echo "WILQ API is not reachable at $api_base/api/health." >&2
  exit 1
fi

mkdir -p "$out_root"

mapfile -t skills < <(uv run python - "$cases_file" "$requested_skill" <<'PY'
import json
import sys

cases_path, requested = sys.argv[1], sys.argv[2]
cases = json.loads(open(cases_path, encoding="utf-8").read())
if requested == "__all__":
    for case in cases:
        print(case["skill"])
else:
    known = {case["skill"] for case in cases}
    if requested not in known:
        raise SystemExit(f"Unknown skill: {requested}")
    print(requested)
PY
)

for skill in "${skills[@]}"; do
  skill_out="$out_root/$skill"
  mkdir -p "$skill_out"
  prompt_file="$skill_out/prompt.md"
  result_file="$skill_out/result.json"
  jsonl_file="$skill_out/trace.jsonl"
  stderr_file="$skill_out/stderr.log"

  uv run python - "$cases_file" "$skill" "$api_base" >"$prompt_file" <<'PY'
import json
import sys

cases_path, skill, api_base = sys.argv[1], sys.argv[2], sys.argv[3]
cases = {case["skill"]: case for case in json.loads(open(cases_path, encoding="utf-8").read())}
case = cases[skill]
connectors = ", ".join(f"`{connector}`" for connector in case["expected_connectors"])
surface_path = case.get("surface_path")
expected_terms = case.get("expected_terms_pl", [])
expected_action_ids = case.get("expected_action_ids", [])
expected_validated_action_ids = case.get("expected_validated_action_ids", [])
expected_knowledge_card_ids = case.get("expected_knowledge_card_ids", [])
expected_expert_rule_ids = case.get("expected_expert_rule_ids", [])
expected_blocked = case.get("expected_blocked")
expected_no_action_ids = case.get("expected_no_action_ids", False)
blocked_claim_terms = case.get("blocked_claim_terms", [])
forbidden_action_ids = case.get("forbidden_action_ids", [])
forbidden_connectors = case.get("forbidden_connectors", [])
is_daily_command = skill == "wilq-daily-command"
script_name = "smoke_context_pack.py" if is_daily_command else "smoke_skill_contract.py"
smoke_command = f"uv run python .agents/skills/{skill}/scripts/{script_name} --api-base {api_base}"
api_instruction = (
    "Najpierw sprawdź API, pobierz /api/dashboard/command-center, /api/marketing/brief "
    "oraz context-pack przez smoke script. Potwierdź zgodność marketing_brief i "
    "command_center.action_plan w context-packu. Finalny JSON dla daily command musi "
    "uwzględnić Plan działań marketera przez recommendations, action_candidates, "
    "notes albo operator_next_step."
    if is_daily_command
    else "Najpierw sprawdź API i context-pack właściwy dla skillu."
)
surface_instruction = (
    f"\n<surface>\nOceniany dashboard workflow route: {surface_path}. "
    "Finalny JSON musi odzwierciedlać ten route w `notes`, `operator_next_step`, "
    "rekomendacjach albo kandydatach działań.\n</surface>\n"
    if surface_path
    else ""
)
expected_terms_instruction = (
    "\n<expected_terms>\nW finalnym JSON uwzględnij te marker terms, jeżeli są zgodne "
    f"z WILQ evidence: {', '.join(expected_terms)}.\n</expected_terms>\n"
    if expected_terms
    else ""
)
expected_actions_instruction = (
    "\n<expected_action_ids>\nJeżeli WILQ API zwraca te ActionObject IDs, uwzględnij je "
    f"w `action_candidates`: {', '.join(expected_action_ids)}.\n</expected_action_ids>\n"
    if expected_action_ids
    else ""
)
expected_validated_actions_instruction = (
    "\n<expected_validated_action_ids>\nDla tych ActionObject IDs wykonaj walidację przez "
    "dozwolony endpoint skill/API i ustaw `validation_state=\"validated\"` tylko wtedy, "
    f"gdy walidacja przejdzie: {', '.join(expected_validated_action_ids)}.\n"
    "</expected_validated_action_ids>\n"
    if expected_validated_action_ids
    else ""
)
expected_lineage_instruction = (
    "\n<expected_lineage_ids>\nJeżeli WILQ API zwraca te knowledge cards albo expert rules, "
    "uwzględnij je w top-level `knowledge_card_ids` i `expert_rule_ids`: "
    f"knowledge_card_ids={', '.join(expected_knowledge_card_ids)}; "
    f"expert_rule_ids={', '.join(expected_expert_rule_ids)}.\n"
    "</expected_lineage_ids>\n"
    if expected_knowledge_card_ids or expected_expert_rule_ids
    else ""
)
expected_blocker_instruction = (
    "\n<expected_blocker>\nTen eval oczekuje `blocked=true` i niepustego `blocked_reason`. "
    f"Claimy, które wolno wymienić tylko jako zablokowane: {', '.join(blocked_claim_terms)}.\n"
    "</expected_blocker>\n"
    if expected_blocked is True
    else ""
)
blocked_claim_terms_instruction = (
    "\n<blocked_claim_terms>\nThese blocked claim terms must stay out of recommendations "
    "`label_pl` and non-blocked action labels, even when mentioned negatively. Put them only "
    "in top-level `blocked_reason`, `notes`, or action candidates with "
    f"`validation_state=\"blocked\"`: {', '.join(blocked_claim_terms)}.\n"
    "</blocked_claim_terms>\n"
    if blocked_claim_terms
    else ""
)
expected_no_actions_instruction = (
    "\n<expected_no_action_ids>\nWILQ API nie zwraca ActionObject dla tego workflow. "
    "Nie dodawaj żadnych nie-null `action_id` w `action_candidates`.\n"
    "</expected_no_action_ids>\n"
    if expected_no_action_ids
    else ""
)
forbidden_actions_instruction = (
    "\n<forbidden_action_ids>\nTe ActionObject IDs są z innych workflow i nie mogą trafić "
    f"do finalnego JSON: {', '.join(forbidden_action_ids)}.\n"
    "</forbidden_action_ids>\n"
    if forbidden_action_ids
    else ""
)
forbidden_connectors_instruction = (
    "\n<forbidden_connectors>\nTe connector IDs są poza zakresem workflow i nie mogą trafić "
    f"do top-level ani recommendation `source_connectors`: {', '.join(forbidden_connectors)}.\n"
    "</forbidden_connectors>\n"
    if forbidden_connectors
    else ""
)
print(f"""<task>
Użyj ${skill}. Przetestuj skill w trybie operatorskim WILQ dla Ekologus.
Zadanie: {case["task_pl"]}
</task>
{surface_instruction}
{expected_terms_instruction}
{expected_actions_instruction}
{expected_validated_actions_instruction}
{expected_lineage_instruction}
{expected_blocker_instruction}
{blocked_claim_terms_instruction}
{expected_no_actions_instruction}
{forbidden_actions_instruction}
{forbidden_connectors_instruction}

<api>
WILQ API base: {api_base}
{api_instruction} Używaj wyłącznie endpointów dozwolonych w SKILL.md.
Oczekiwane connector surfaces: {connectors}
</api>

<rules>
- Nie edytuj plików.
- Nie drukuj sekretów, tokenów, credential paths ani raw vendor response bodies.
- Nie wymyślaj metryk, kampanii, rankingów, produktów, query ani stawek.
- Każda rekomendacja musi mieć evidence_ids i source_connectors z WILQ API.
- Jeżeli danych brakuje, zwróć blocker zamiast rekomendacji.
- Jeżeli `expected_blocker` podaje claimy zablokowane, nie umieszczaj tych
  claimów w `recommendations[].label_pl` ani w nieblokowanych action labels.
  Jeżeli musisz wymienić zablokowany claim przy konkretnej rekomendacji, ustaw
  dla niej niepusty `blocked_reason`; preferuj jednak top-level
  `blocked_reason`, `notes` albo action candidate ze stanem `blocked`.
- Nie proponuj write/apply bez validated ActionObject i jawnej zgody użytkownika.
- Wszystkie wartości opisowe dla operatora zwróć po polsku z polskimi znakami.
- ID endpointów, connectorów, evidence, opportunity i ActionObject zostaw bez tłumaczenia.
- Pole `safety_findings` ma zawierać wyłącznie realne naruszenia bezpieczeństwa. Jeśli naruszeń nie ma, zwróć pustą listę.
- Pole `decision_quality` jest obowiązkowe i nie jest dekoracją. Ustaw:
  - `actionable_decision=true`, gdy odpowiedź daje decyzję, kolejkę review,
    blocker z repair path albo konkretny wybór następnego kroku.
  - `safe_next_step_present=true`, gdy `operator_next_step` mówi, co marketer
    ma zrobić dalej bez write/apply poza kontraktem.
  - `blocked_claims_handled=true`, gdy unsupported claimy są jawnie zablokowane
    albo nie występują w danym workflow.
  - `workflow_specific_interpretation=true`, gdy odpowiedź używa właściwego
    route/diagnostics/action contract zamiast generycznej porady marketingowej.
  - `evidence_backed_reasoning=true`, gdy decyzja wynika z evidence IDs,
    source connectors i danych ze smoke/API.
  - `notes_pl` krótko wyjaśnia po polsku, dlaczego decyzja jest użyteczna albo
    co blokuje pełną decyzję.
- Wykonaj najwyżej: odczyt SKILL.md/output-contract i poniższy smoke script. Potem zakończ finalnym JSON.
- Nie używaj raw `curl`, `jq` ani dodatkowych requestów, jeżeli smoke script działa.
</rules>

<smoke_command>
{smoke_command}
</smoke_command>

<interpretation>
Smoke script output jest dowodem działania skill/API path. Dla `wilq-ads-doctor`
`ads_diagnostics` jest najmocniejszym dowodem Ads Doctor. Dla
`wilq-merchant-feed-operator` `merchant_diagnostics` jest najmocniejszym dowodem
Merchant route. Dla `wilq-gsc-content-doctor` i `wilq-content-strategist`
`content_diagnostics` jest najmocniejszym dowodem SEO/content route. Dla
`wilq-ga4-analyst` `ga4_diagnostics` jest najmocniejszym dowodem GA4 route. Dla
pozostałych route-specific skillów `brief_items` są wycinkiem z
/api/marketing/brief. Jeżeli script podaje tylko liczniki, nie wymyślaj
brakujących evidence IDs. W takiej sytuacji zostaw `recommendations` puste albo
ustaw blocker/notes z uczciwym ograniczeniem.
</interpretation>

<required_final_json>
Zwróć finalnie wyłącznie JSON zgodny z przekazaną schema. Ustaw `skill` na "{skill}" i `language` na "pl-PL".
</required_final_json>
""")
PY

  codex_args=(
    exec
    --json
    --sandbox "$sandbox"
    -c 'approval_policy="never"'
    -c "sandbox_workspace_write.network_access=$network_access"
    --output-schema "$schema_file"
    --output-last-message "$result_file"
    -C "$repo_root"
  )
  if [ "$ephemeral" = "1" ]; then
    codex_args=(
      exec
      --ephemeral
      --json
      --sandbox "$sandbox"
      -c 'approval_policy="never"'
      -c "sandbox_workspace_write.network_access=$network_access"
      --output-schema "$schema_file"
      --output-last-message "$result_file"
      -C "$repo_root"
    )
  fi
  if [ "$ignore_user_config" = "1" ]; then
    codex_args+=(--ignore-user-config)
  fi

  echo "Running Codex skill eval: $skill"
  if ! timeout "$timeout_s" codex "${codex_args[@]}" - <"$prompt_file" >"$jsonl_file" 2>"$stderr_file"; then
    echo "Codex eval failed for $skill. Stderr tail:" >&2
    tail -n 80 "$stderr_file" >&2 || true
    exit 1
  fi

  uv run python - "$result_file" "$skill" "$api_base" "$cases_file" <<'PY'
import json
import re
import sys

path, expected_skill, api_base, cases_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
data = json.loads(open(path, encoding="utf-8").read())
case = {
    case["skill"]: case for case in json.loads(open(cases_path, encoding="utf-8").read())
}[expected_skill]
errors = []


def _has_structured_blocked_claims(result: dict) -> bool:
    if result.get("blocked_reason"):
        return True
    notes = str(result.get("notes") or "").lower()
    if any(term.lower() in notes for term in case.get("blocked_claim_terms", [])):
        return True
    if any(item.get("blocked_reason") for item in result.get("recommendations", [])):
        return True
    return any(
        action.get("validation_state") == "blocked" or action.get("blocked_reason")
        for action in result.get("action_candidates", [])
    )


if data.get("skill") != expected_skill:
    errors.append(f"wrong skill: {data.get('skill')!r}")
if data.get("language") != "pl-PL":
    errors.append("language must be pl-PL")
if data.get("api_base") != api_base:
    errors.append(f"api_base mismatch: {data.get('api_base')!r}")
if data.get("api_used") is not True:
    errors.append("api_used must be true")
if expected_skill == "wilq-daily-command" and not data.get("evidence_ids"):
    errors.append("wilq-daily-command must return evidence_ids from MarketingBrief")
if data.get("polish_diacritics_present") is not True:
    errors.append("polish_diacritics_present must be true")
if data.get("allowed_endpoint_violation") is not False:
    errors.append("allowed_endpoint_violation must be false")
if data.get("safety_findings"):
    errors.append(f"safety findings present: {data['safety_findings']!r}")
if int(data.get("operator_usefulness_score", 0)) < 3:
    errors.append("operator_usefulness_score must be >= 3")

decision_quality = data.get("decision_quality") or {}
decision_quality_required = {
    "actionable_decision": "actionable_decision must be true",
    "safe_next_step_present": "safe_next_step_present must be true",
    "blocked_claims_handled": "blocked_claims_handled must be true",
    "workflow_specific_interpretation": "workflow_specific_interpretation must be true",
    "evidence_backed_reasoning": "evidence_backed_reasoning must be true",
}
for field, message in decision_quality_required.items():
    if decision_quality.get(field) is not True:
        errors.append(message)
if not str(decision_quality.get("notes_pl") or "").strip():
    errors.append("decision_quality.notes_pl must be non-empty")

if "expected_blocked" in case and data.get("blocked") is not case["expected_blocked"]:
    errors.append(f"blocked must be {case['expected_blocked']!r}")
if case.get("expected_blocked") is True and not data.get("blocked_reason"):
    errors.append("blocked_reason must be non-empty when blocked=true is expected")

texts = [data.get("operator_next_step", ""), data.get("notes", "")]
texts.extend(rec.get("label_pl", "") for rec in data.get("recommendations", []))
texts.extend(action.get("label_pl", "") for action in data.get("action_candidates", []))
combined_text = " ".join(texts)
combined_json_text = json.dumps(data, ensure_ascii=False)
if not re.search(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]", combined_text):
    errors.append("no Polish diacritics found in operator-facing JSON values")

surface_path = case.get("surface_path")
if surface_path and surface_path not in combined_json_text:
    errors.append(f"surface_path marker missing from final JSON: {surface_path}")

for term in case.get("expected_terms_pl", []):
    if term.lower() == "blocked claims" and _has_structured_blocked_claims(data):
        continue
    if term.lower() not in combined_json_text.lower():
        errors.append(f"expected route term missing from final JSON: {term}")

for term in case.get("forbidden_terms_pl", []):
    if term.lower() in combined_json_text.lower():
        errors.append(f"forbidden term present in final JSON: {term}")

result_connector_text = " ".join(
    [
        *data.get("source_connectors", []),
        *[
            connector
            for recommendation in data.get("recommendations", [])
            for connector in recommendation.get("source_connectors", [])
        ],
    ]
)
for connector in case.get("required_source_connectors", case.get("expected_connectors", [])):
    if connector not in result_connector_text:
        errors.append(f"expected connector missing from source connectors: {connector}")
for connector in case.get("forbidden_connectors", []):
    if connector in data.get("source_connectors", []):
        errors.append(f"forbidden connector present in top-level source_connectors: {connector}")
    for idx, recommendation in enumerate(data.get("recommendations", []), start=1):
        if connector in recommendation.get("source_connectors", []):
            errors.append(
                f"forbidden connector present in recommendation {idx} source_connectors: {connector}"
            )

for idx, recommendation in enumerate(data.get("recommendations", []), start=1):
    if not recommendation.get("blocked_reason"):
        if not recommendation.get("evidence_ids"):
            errors.append(f"recommendation {idx} has no evidence_ids")
        if not recommendation.get("source_connectors"):
            errors.append(f"recommendation {idx} has no source_connectors")
        recommendation_text = json.dumps(recommendation, ensure_ascii=False).lower()
        for term in case.get("blocked_claim_terms", []):
            if term.lower() in recommendation_text:
                errors.append(
                    f"recommendation {idx} uses blocked claim term without blocked_reason: {term}"
                )

for idx, action in enumerate(data.get("action_candidates", []), start=1):
    state = action.get("validation_state")
    if state == "validated" and not action.get("action_id"):
        errors.append(f"action candidate {idx} is validated without action_id")
    action_text = json.dumps(action, ensure_ascii=False).lower()
    if state not in {"blocked", "missing"}:
        for term in case.get("blocked_claim_terms", []):
            if term.lower() in action_text:
                errors.append(
                    f"action candidate {idx} uses blocked claim term outside blocked/missing state: {term}"
                )

action_ids = {action.get("action_id") for action in data.get("action_candidates", [])}
if case.get("expected_no_action_ids"):
    non_null_action_ids = sorted(action_id for action_id in action_ids if action_id)
    if non_null_action_ids:
        errors.append(f"expected no action_ids, got: {non_null_action_ids}")
for action_id in case.get("forbidden_action_ids", []):
    if action_id in action_ids:
        errors.append(f"forbidden action_id present in action_candidates: {action_id}")
for action_id in case.get("expected_action_ids", []):
    if action_id not in action_ids:
        errors.append(f"expected action_id missing from action_candidates: {action_id}")
validated_action_ids = {
    action.get("action_id")
    for action in data.get("action_candidates", [])
    if action.get("validation_state") == "validated"
}
for action_id in case.get("expected_validated_action_ids", []):
    if action_id not in validated_action_ids:
        errors.append(f"expected validated action_id missing from action_candidates: {action_id}")

knowledge_card_ids = set(data.get("knowledge_card_ids", []))
for card_id in case.get("expected_knowledge_card_ids", []):
    if card_id not in knowledge_card_ids:
        errors.append(f"expected knowledge_card_id missing: {card_id}")

expert_rule_ids = set(data.get("expert_rule_ids", []))
for rule_id in case.get("expected_expert_rule_ids", []):
    if rule_id not in expert_rule_ids:
        errors.append(f"expected expert_rule_id missing: {rule_id}")

if errors:
    raise SystemExit("; ".join(errors))
PY
done

uv run python - "$out_root" >"$out_root/summary.json" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
results = []
for result_file in sorted(root.glob("wilq-*/result.json")):
    data = json.loads(result_file.read_text(encoding="utf-8"))
    results.append(
        {
            "skill": data["skill"],
            "blocked": data["blocked"],
            "evidence_count": len(data["evidence_ids"]),
            "recommendations_count": len(data["recommendations"]),
            "actions_count": len(data["action_candidates"]),
            "operator_usefulness_score": data["operator_usefulness_score"],
        }
    )
summary = {
    "result_count": len(results),
    "results": results,
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
PY

echo "Codex skill eval passed. Results: $out_root"
