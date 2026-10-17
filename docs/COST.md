# Cost

Providers in this table are simulated profiles. Accuracy is configured or lexical, so the quality column is not a model measurement. Token counts are a character/4 heuristic plus a per-profile overhead (`token_note` in `docs/results/summary.json`). Latency is not measured: the eval clock is frozen. A fake clock is not a p50.

Prices are **[EST] placeholders** chosen for arithmetic: USD 1.00 per million input tokens and USD 3.00 per million output tokens. They are not a vendor price. Date of the token measurement: 2026-10-17. Command: `python -m triage_lab eval`. Package 0.1.0. Commit `283f08ecee0aca3f088bc045aa87e2d392687fb3`.

Human review: **[EST] USD 1.00 per escalated ticket**.

| Scenario | Model/provider | Tokens in/out per ticket (simulated) | Cost/ticket [EST] | Cost / 1,000 [EST] | p50/p95 latency | Quality | Price date/source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rules_baseline | keyword lexicon, fake | 103.816 / 36 | 0.000212 | 0.212 | not measured | fake lexicon; dev constraint not met | [EST] 2026-10-17, not a vendor card |
| small_sim | error-profile fake, flip 1/5 | 255.816 / 80 | 0.000496 | 0.496 | not measured | simulated by construction | [EST] 2026-10-17 |
| large_sim | error-profile fake, flip 1/17 | 735.816 / 130 | 0.001126 | 1.126 | not measured | simulated by construction | [EST] 2026-10-17 |
| cascade | small, then large if confidence < tau | 991.632 / 210 | 0.001622 | 1.622 | not measured | same labels as large on this draw; simulated | [EST] 2026-10-17 |
| live | not run | not measured | not measured | not measured | not measured | not measured | none |

Arithmetic: `(tokens_in * 1.00 + tokens_out * 3.00) / 1e6`.

Blended cost per ticket **[EST]** = model cost + test human share * 1.00 (auto-error term is 0 on the profiles that met the dev constraint):

| Scenario | Test human share (measured route share) | Blended USD/ticket [EST] |
| --- | --- | --- |
| rules_baseline | 0.8736 | 0.874 |
| small_sim | 0.8621 | 0.863 |
| large_sim | 0.5977 | 0.599 |
| cascade | 0.8276 | 0.829 |

`rules_baseline` and `small_sim` did not meet the 2% dev auto-error constraint. Their tau is the most conservative candidate (0.99). Do not read the blended saving as an approved operating point for those two.

## Monthly volume sensitivity [EST]

Model column uses the per-ticket [EST] cost times volume. Blended uses the large_sim blended figure only as an illustration of staffing, not as a forecast.

| Tickets / month | rules model USD | large model USD | cascade model USD | large blended USD |
| --- | --- | --- | --- | --- |
| 1,000 | 0.21 | 1.13 | 1.62 | 599 |
| 10,000 | 2.12 | 11.26 | 16.22 | 5,990 |
| 50,000 | 10.59 | 56.29 | 81.08 | 29,950 |

The blended column is almost entirely the human placeholder. Token price does not decide the case until the human share drops.
