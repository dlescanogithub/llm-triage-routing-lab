# Business case

Fictional shop: Almacén Brújula. No fees were charged and none are quoted as real.

## Baseline

All-human triage. Placeholder handling time **[EST] 4 minutes** per ticket at **[EST] USD 15 per hour**, which is **[EST] USD 1.00 per ticket**. Misroute cost is separate: a billing ticket sent to FAQ can become a complaint. Placeholder **[EST] USD 8.00** per misrouted auto-reply (goodwill plus a second touch). These two numbers are inputs, not measurements.

## ROI formula

```
model_usd = (tokens_in / 1e6) * price_in + (tokens_out / 1e6) * price_out
blended_usd = model_usd + human_share * human_usd + auto_error * misroute_usd
saving_usd = human_usd - blended_usd
```

`human_share` and `auto_error` come from the test split of a named run. `tokens_*` in this repo are simulated (character heuristic plus profile overhead). `price_in` and `price_out` used below are **[EST] 1.00 and 3.00 USD per million tokens**. `human_usd` is **[EST] 1.00**.

Worked example for `large_sim` on the 2026-10-17 run (`python -m triage_lab eval`, commit `d5f1a0ec694a34dd2977db170820abf25f9ddb06`, package 0.1.0). The token term ignores cached tokens:

- simulated tokens 989.207 / 130 per ticket
- model_usd = 0.001379
- human_share = 0.5977, auto_error among auto-routed = 0.0000
- blended_usd = 0.001379 + 0.5977 * 1.00 + 0 = 0.599 **[EST]**
- saving vs all-human = 0.401 USD/ticket **[EST]**

That saving is only as good as the human share. On this draw the dev constraint (auto-routed error <= 2%) forces tau 0.90 and still leaves about 60% of test tickets with a person. `rules_baseline` and `small_sim` do not meet the dev constraint at any tau; their reported tau is 0.99 and the human share is about 0.87. Do not use the 0.9655 accuracy of `large_sim` in this formula: that accuracy is simulated by construction.

If auto-error were 2% on a 40% auto-route share, misroute would add 0.40 * 0.02 * 8.00 = 0.064 USD/ticket **[EST]**. The gate's job is to keep that term small.

## What would change the case

A re-verification with a named model, a per-model price, and a ledger. The 2026-10-17 check classified 0/40. Volume sensitivity is in `docs/COST.md`.
