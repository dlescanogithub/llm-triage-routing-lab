# Cost

Providers in this table are simulated profiles. Accuracy is configured or lexical, so the quality column is not a model measurement. Token counts are a character/4 heuristic plus a per-profile overhead (`token_note` in `docs/results/summary.json`). Latency is not measured: the eval clock is frozen. A fake clock is not a p50.

Prices are **[EST] placeholders** chosen for arithmetic: USD 1.00 per million input tokens and USD 3.00 per million output tokens. They are not a vendor price. Date of the token measurement: 2026-10-23, on the English corpus. Command: `python -m triage_lab eval`. Package 0.1.1. Commit `4e32b1c1bfade248a9b747f0feb3fa0dbe5ee23c`. This estimate ignores cached tokens: it multiplies reported or simulated prompt tokens by the input price and does not apply a cache discount.

Human review: **[EST] USD 1.00 per escalated ticket**.

| Scenario | Model/provider | Tokens in/out per ticket (simulated) | Cost/ticket [EST] | Cost / 1,000 [EST] | p50/p95 latency | Quality | Price date/source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rules_baseline | keyword lexicon, fake | 356.172 / 36 | 0.000464 | 0.464 | not measured | fake lexicon; dev constraint not met | [EST] 2026-10-23, not a vendor card |
| small_sim | error-profile fake, flip 1/5 | 508.172 / 80 | 0.000748 | 0.748 | not measured | simulated by construction | [EST] 2026-10-23 |
| large_sim | error-profile fake, flip 1/17 | 988.172 / 130 | 0.001378 | 1.378 | not measured | simulated by construction | [EST] 2026-10-23 |
| cascade | small, then large if confidence < tau | 1496.345 / 210 | 0.002126 | 2.126 | not measured | same labels as large on this draw; simulated | [EST] 2026-10-23 |
| live | grok-4.20-0309-non-reasoning | not stored | not measured here | not measured | not measured | 82–83/87, n=87, measured by independent verification. First check 0/40: prompt without taxonomy, corrected | 2026-10-17, last run US$0.0391 |

Arithmetic: `(tokens_in * 1.00 + tokens_out * 3.00) / 1e6`.

Blended cost per ticket **[EST]** = model cost + test human share * 1.00 (auto-error term is 0 on the profiles that met the dev constraint):

| Scenario | Test human share (measured route share) | Blended USD/ticket [EST] |
| --- | --- | --- |
| rules_baseline | 0.8736 | 0.874 |
| small_sim | 0.8621 | 0.863 |
| large_sim | 0.1724 | 0.174 |
| cascade | 0.8391 | 0.841 |

`rules_baseline` and `small_sim` did not meet the 2% dev auto-error constraint. Their tau is the most conservative candidate (0.99). Do not read the blended saving as an approved operating point for those two.

## Monthly volume sensitivity [EST]

Model column uses the per-ticket [EST] cost times volume. Blended uses the large_sim blended figure only as an illustration of staffing, not as a forecast.

| Tickets / month | rules model USD | large model USD | cascade model USD | large blended USD |
| --- | --- | --- | --- | --- |
| 1,000 | 0.46 | 1.38 | 2.13 | 174 |
| 10,000 | 4.64 | 13.78 | 21.26 | 1,740 |
| 50,000 | 23.20 | 68.90 | 106.30 | 8,700 |

The blended column is almost entirely the human placeholder. Token price does not decide the case until the human share drops.

A comparative live check that used one price for every model recorded **0.0044 USD** for `grok-4.3` against about **0.0131 USD** at that model's own rate (2026-10-17, reported from the run, not recomputed here). `LLM_MODEL_PRICE_TABLE` now prices each model, and a missing row aborts before the call. Those live figures also ignore cached tokens.

Independent checks the same day, measured by independent verification on the previous bilingual corpus (not re-run on the English-only rows), used `grok-4.20-0309-non-reasoning` at temperature 0 on the test split (n=87): schema-valid 87/87, accuracy 82/87 and 83/87 (range 82–83/87; 83/87 is 95.4%). Last run cost US$0.0391. The repo estimate 0.0675 ignores cached tokens. Attack block on that split is n=4, not conclusive. Benign over-block is n/a (n=0). The earlier 0/40 result is history only: prompt without taxonomy, corrected. The per-ticket [EST] rows above follow the simulated token table.
