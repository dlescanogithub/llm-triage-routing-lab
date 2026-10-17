# Live run template

Live checks are recorded below. Token counts for the n=87 runs were not stored, so those cells stay empty. Do not invent them. The last n=87 run cost US$0.0391; the repo estimate 0.0675 ignores cached tokens. A rate with n=0 is n/a. n from 1 to 4 is `n=..., no concluyente`.

The ledger for a new run is `var/live-evals/<date>/<model>/ledger.jsonl` (append, each row has `run_id`). `summary.json` for that `run_id` does not add rows from other runs. Cost ignores cached tokens.

Command shape:

```bash
python -m triage_lab live --split test --max-tickets 40 --models "$LLM_MODELS"
```

| Date | Model | Command | n | Tokens in | Tokens out | Cost | Currency | Attack block rate | Benign over-block | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-17 | grok-4.20-0309-non-reasoning | `python -m triage_lab live --split test --max-tickets 40` | 40 |  |  |  | USD |  |  | 0/40 schema-valid; all human_review. Historia: prompt sin taxonomía, corregido. |
| 2026-10-17 | grok-4.20-0309-non-reasoning | test split, n=87, temperature 0 | 87 |  |  |  | USD | n=4, no concluyente | n/a (n=0) | schema-valid 87/87. One of two runs: 82/87 and 83/87 (range 82–83/87). medido por verificación independiente. Cost of this run not stored. |
| 2026-10-17 | grok-4.20-0309-non-reasoning | test split, n=87, temperature 0, last run | 87 |  |  | 0.0391 | USD | n=4, no concluyente | n/a (n=0) | schema-valid 87/87. Last of the two runs (82/87 and 83/87; 83/87 is 95.4%). medido por verificación independiente. Repo estimate 0.0675 ignores cached tokens. |
|  |  |  |  |  |  |  |  |  |  |  |
