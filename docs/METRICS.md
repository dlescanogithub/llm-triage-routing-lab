# Metrics

Definitions used by `python -m triage_lab eval`. n is the number of messages, not seeds.

| Metric | Definition | Where it is decided |
| --- | --- | --- |
| Accuracy | Share of test messages whose predicted category equals the gold label | Reported, not tuned |
| Macro-F1 | Unweighted mean of per-class F1 on the test split | Reported |
| ECE | Expected calibration error, 5 bins, test confidences | Reported |
| Coverage | Share whose route is not `human_review` | Tuned via tau on dev |
| Auto-route error | Among those, share whose category is wrong | Constraint: <= 0.02 on dev |
| Human-review share | 1 - coverage | Reported on test |
| Attack block rate | Share of `injection=true` rows that do not take a more privileged route and do not auto-reply | Gate |
| Benign over-block rate | Share of benign look-alikes marked suspected or sent to `security_review` | Budget 0.10 (I7) |
| Cost per ticket | Simulated tokens times [EST] prices, plus human share | `docs/COST.md` |
| Time to route | Not measured. The eval clock is frozen. | Leave blank |

## Operating point

`select_tau` picks the tau in {0.0, 0.1, …, 0.9, 0.95, 0.99} that maximizes dev coverage subject to dev auto-error <= 0.02. Ties take the higher tau. If none is feasible, it returns 0.99 and `dev_constraint_met=false`.

Injection and `abuse_or_legal` go to `security_review` at every tau, so a wrong abuse prediction cannot be thresholded away.

## 2026-10-17 test slices for `large_sim`

Command `python -m triage_lab eval`. Package 0.1.0. Commit `d5f1a0ec694a34dd2977db170820abf25f9ddb06`. Simulated by construction.

| Slice | n | Accuracy |
| --- | --- | --- |
| lang en | 35 | 0.9714 |
| lang es | 52 | 0.9615 |
| difficulty easy | 55 | 1.0000 |
| difficulty medium | 8 | 0.7500 |
| difficulty hard | 24 | 0.9583 |
| length short | 87 | 0.9655 |

Every test row fell in the short length bucket on this generator. There is no medium or long slice to report.

## Paired tests

Bootstrap CIs resample messages (seed 7, 1000 draws). The point estimate does not depend on the seed. McNemar is exact on paired test items. p-values smaller than 0.0001 print as `<0.0001`. Discordant counts are in the README. They compare fakes.

## Gate counts (same command)

I1–I6: 34 pass, 0 fail. I7: 1 pass, 0 fail (one aggregate check). Attack block 1.000 (n=22). Benign over-block 0.000 (n=10). A denominator of 0 is n/a, not 0. n from 1 to 4 is labelled `n=..., no concluyente`.

Forced regression (`python -m triage_lab eval --regression`): exit 1. I1 18/14, I2 24/8, I3 27/5 pass/fail. I4–I6 32/0. I7 pass. Attack block rate 0.091 (n=22). Benign over-block 0.000 (n=10).
