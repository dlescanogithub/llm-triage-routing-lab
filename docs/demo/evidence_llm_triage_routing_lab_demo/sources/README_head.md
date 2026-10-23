# llm-triage-routing-lab

[![ci](https://github.com/dlescanogithub/llm-triage-routing-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/dlescanogithub/llm-triage-routing-lab/actions/workflows/ci.yml)

## Start here

On the committed synthetic files, the control gate records zero invariant failures, and the forced regression exits 1 when the sanitizer and the allowlist are turned off.
One command, no key and no network: `python -m triage_lab demo`.
Walkthrough: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md). The unit-test line measured on 2026-10-23 is in [Proof](#proof).

Offline lab for one support inbox. The shop, Brujula Store, is fictional. Providers in CI are deterministic fakes. They exercise the harness, the invariants, and the controls. They do not measure a model.

> **Honest limits.** Fake-versus-fake accuracy is **SIMULATED** by construction (`small_sim` flips about 1 id in 5, `large_sim` about 1 in 17). Do not quote it as model quality. A separate live check, **MEASURED** on 2026-10-17 on the previous bilingual corpus and not re-run on the English-only rows, is not part of CI: `grok-4.20-0309-non-reasoning`, temperature 0, test split, 87 messages, schema-valid 87 of 87, accuracy 82 of 87 and 83 of 87 on two runs. [docs/LIVE_RUN_TEMPLATE.md](docs/LIVE_RUN_TEMPLATE.md) labels that check as measured by independent verification. Attack block on that live split has 4 messages, which this lab treats as inconclusive. Benign over-block on that split has a zero denominator, so the rate is not applicable. Last run cost US$0.0391. The repo estimate 0.0675 ignores cached tokens. Token counts for those runs were not stored. Latency was not measured.

## Problem and result

A support inbox needs a classifier that cannot be talked into a refund or an auto-reply. The result this repo stands on is the control gate, not a model score.

On 2026-10-23, package 0.1.1, commit `4e32b1c1bfade248a9b747f0feb3fa0dbe5ee23c`, command `python -m triage_lab eval`, remeasured on the English corpus: **0 invariant failures**. Attack block rate **1.000 on 22 messages** (the eval prints `1.000 (n=22)`) and benign over-block **0.000 on 10 messages** (the eval prints `0.000 (n=10)`) on the known-marker file `data/adversarial.jsonl`. I1 through I6 are counted on 34 messages: the 32-row adversarial file plus two probes (`compromised_sim` and `invalid_sim`). Each of I1–I6 is 34 pass and 0 fail. I7 is one aggregate check: 1 pass and 0 fail. The attack and benign denominators stay on the file slices (22 and 10). The probes are not in those denominators. Profile accuracy in the table below is simulated and is not this result.

The same date has the live check in the callout above. An earlier same-day check classified 0 of 40 because the prompt did not include the taxonomy. That prompt was corrected. The 0 of 40 figure is history, not the result to cite.

## Quickstart

Cost of the default path: **zero**. No API key is read. No network call is made.

```bash
python -m pip install -e ".[dev]"
python -m triage_lab demo
```

`make setup` and `make demo` are the same two steps. `make` may be absent. The `python -m` forms are enough.

**MEASURED** 2026-10-23, package 0.1.1, provider `large_sim`. Stdout was these three lines:

```text
demo-1 category=product_question route=auto_reply_faq injection=False
demo-2 category=order_status route=logistics_queue injection=False
demo-3 category=product_question route=security_review injection=True
```
