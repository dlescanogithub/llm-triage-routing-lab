# Cost

Providers in this table are simulated profiles. Accuracy is configured or lexical, so the quality column is not a model measurement. Token counts are a character/4 heuristic plus a per-profile overhead (`token_note` in `docs/results/summary.json`). Latency is not measured: the eval clock is frozen. A fake clock is not a p50.

Prices are **[EST] placeholders** chosen for arithmetic: USD 1.00 per million input tokens and USD 3.00 per million output tokens. They are not a vendor price. Date of the token measurement: 2026-10-17. Command: `python -m triage_lab eval`. Package 0.1.0. Commit `d5f1a0ec694a34dd2977db170820abf25f9ddb06`. This estimate ignores cached tokens: it multiplies reported or simulated prompt tokens by the input price and does not apply a cache discount.

Human review: **[EST] USD 1.00 per escalated ticket**.

| Scenario | Model/provider | Tokens in/out per ticket (simulated) | Cost/ticket [EST] | Cost / 1,000 [EST] | p50/p95 latency | Quality | Price date/source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rules_baseline | keyword lexicon, fake | 357.207 / 36 | 0.000465 | 0.465 | not measured | fake lexicon; dev constraint not met | [EST] 2026-10-17, not a vendor card |
| small_sim | error-profile fake, flip 1/5 | 509.207 / 80 | 0.000749 | 0.749 | not measured | simulated by construction | [EST] 2026-10-17 |
| large_sim | error-profile fake, flip 1/17 | 989.207 / 130 | 0.001379 | 1.379 | not measured | simulated by construction | [EST] 2026-10-17 |
| cascade | small, then large if confidence < tau | 1498.414 / 210 | 0.002128 | 2.128 | not measured | same labels as large on this draw; simulated | [EST] 2026-10-17 |
| live | not re-verified | not measured | not measured | not measured | not measured | 0/40 schema-valid on the first check | see below |

Arithmetic: `(tokens_in * 1.00 + tokens_out * 3.00) / 1e6`.

Blended cost per ticket **[EST]** = model cost + test human share * 1.00 (auto-error term is 0 on the profiles that met the dev constraint):

| Scenario | Test human share (measured route share) | Blended USD/ticket [EST] |
| --- | --- | --- |
| rules_baseline | 0.8736 | 0.874 |
| small_sim | 0.8621 | 0.863 |
| large_sim | 0.5977 | 0.599 |
| cascade | 0.8276 | 0.830 |

`rules_baseline` and `small_sim` did not meet the 2% dev auto-error constraint. Their tau is the most conservative candidate (0.99). Do not read the blended saving as an approved operating point for those two.

## Monthly volume sensitivity [EST]

Model column uses the per-ticket [EST] cost times volume. Blended uses the large_sim blended figure only as an illustration of staffing, not as a forecast.

| Tickets / month | rules model USD | large model USD | cascade model USD | large blended USD |
| --- | --- | --- | --- | --- |
| 1,000 | 0.47 | 1.38 | 2.13 | 599 |
| 10,000 | 4.65 | 13.79 | 21.28 | 5,990 |
| 50,000 | 23.26 | 68.96 | 106.42 | 29,950 |

The blended column is almost entirely the human placeholder. Token price does not decide the case until the human share drops.

A comparative live check that used one price for every model recorded **0.0044 USD** for `grok-4.3` against about **0.0131 USD** at that model's own rate (2026-10-17, reported from the run, not recomputed here). `LLM_MODEL_PRICE_TABLE` now prices each model, and a missing row aborts before the call. Those live figures also ignore cached tokens.
