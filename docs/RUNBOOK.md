# Runbook

Roles: taxonomy owner, tau approver, security, on-call. This lab has no pager.

## Operate

- Default: `python -m triage_lab eval` and `python -m triage_lab demo`. No network.
- Shadow a file: `python -m triage_lab shadow --input data/golden.jsonl`. Effects: none.
- Live, only when the owner sets env and accepts the cap: `LIVE_LLM=1`, `MAX_LIVE_SPEND_USD` > 0, and a price row per model in `LLM_MODEL_PRICE_TABLE` (or `MAX_LIVE_TOKENS` when no price is set and cost stays `unknown`). A missing model price aborts before the call. The ledger cost ignores cached tokens. Then `python -m triage_lab live --split test --max-tickets 40 --models "$LLM_MODELS"`. Never in CI.

## Monitor

Watch, per run: invariant fail counts, attack block rate, benign over-block rate, human-review share, auto-error on the auto-routed slice, simulated or ledgered tokens. Logs are JSON (`ts`, `level`, `msg`, `run_id`). Traces are JSONL.

## Incident: misrouted ticket or suspected injection

1. **Detect.** A customer effect that should not have happened, a tool name outside the route, or a spike in `security_review` / auto-error.
2. **Contain.** Set `FORCE_HUMAN_REVIEW=1`. The pipeline skips the provider and routes every ticket to `human_review`. Confirm with a one-ticket demo in a scratch env.
3. **Recover.** Keep the flag on. Pull the JSONL trace for the `run_id`. If a tool was blocked, the event kind is `tool_blocked`. If the sanitizer missed a phrase, add the marker only after a regression test, and do not claim the list is complete.
4. **Ownership.** Security leads injection. The tau approver leads a bad threshold. The taxonomy owner leads a wrong category.
5. **Rollback.** Revert the taxonomy or tau change. There is no model weight to roll back in this repo. Live stays off until the ledger and the gate are reviewed.
6. **Handoff.** Note the flag, the commit, the command, and whether any live ledger row exists under `var/live-evals/` (gitignored).

## Incident: spend

If a live call would exceed the remaining cap, it is refused before the HTTP call. After the call, reported usage settles the reservation. If prices are unset and `MAX_LIVE_TOKENS` is set, cost is the string `unknown`. The API key is not written to the ledger or to exception text.
