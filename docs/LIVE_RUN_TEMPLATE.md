# Live run template

One live check is recorded below. Tokens and cost from that check are not stored in this repo, so those cells stay empty. Do not invent them. Re-verification is pending after the taxonomy prompt fix.

The ledger for a new run is `var/live-evals/<date>/<model>/ledger.jsonl` (append, each row has `run_id`). `summary.json` for that `run_id` does not add rows from other runs. Cost ignores cached tokens.

Command shape:

```bash
python -m triage_lab live --split test --max-tickets 40 --models "$LLM_MODELS"
```

| Date | Model | Command | n | Tokens in | Tokens out | Cost | Currency | Attack block rate | Benign over-block | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-17 | grok-4.20-0309-non-reasoning | `python -m triage_lab live --split test --max-tickets 40` | 40 |  |  |  | USD |  |  | 0/40 schema-valid; all human_review. Prompt had no category list. Corrected. Re-verification pending. |
|  |  |  |  |  |  |  |  |  |  |  |
