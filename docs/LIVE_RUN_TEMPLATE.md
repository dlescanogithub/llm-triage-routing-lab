# Live run template

Two live checks are recorded below. Tokens and cost are not stored in this repo, so those cells stay empty. Do not invent them. A rate with n=0 is n/a. n from 1 to 4 is `n=..., no concluyente`.

The ledger for a new run is `var/live-evals/<date>/<model>/ledger.jsonl` (append, each row has `run_id`). `summary.json` for that `run_id` does not add rows from other runs. Cost ignores cached tokens.

Command shape:

```bash
python -m triage_lab live --split test --max-tickets 40 --models "$LLM_MODELS"
```

| Date | Model | Command | n | Tokens in | Tokens out | Cost | Currency | Attack block rate | Benign over-block | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-17 | grok-4.20-0309-non-reasoning | `python -m triage_lab live --split test --max-tickets 40` | 40 |  |  |  | USD |  |  | 0/40 schema-valid; all human_review. Prompt had no category list. |
| 2026-10-17 | not stored here | test split, n=87 | 87 |  |  |  | USD | n=4 on the golden test split, rate not stored, no concluyente | n/a (n=0) | schema-valid 87/87, accuracy 82/87. The golden test split has 4 injection rows and 0 benign look-alikes. |
|  |  |  |  |  |  |  |  |  |  |  |
