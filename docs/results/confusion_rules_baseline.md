# Confusion matrix: rules_baseline

Generated: 2026-10-17 (UTC)

Command: `python -m triage_lab eval`

Package version: 0.1.0

Git commit: `d5f1a0ec694a34dd2977db170820abf25f9ddb06`

Split: test

n: 87

Simulated profile. This matrix checks the comparison harness, not a real model.

| gold \\ pred | order_status | shipping_address_change | refund_request | payment_issue | product_question | complaint | abuse_or_legal | spam | other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| order_status | 10 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| shipping_address_change | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| refund_request | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 3 |
| payment_issue | 0 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 2 |
| product_question | 1 | 0 | 1 | 0 | 8 | 0 | 0 | 0 | 3 |
| complaint | 0 | 0 | 1 | 0 | 0 | 10 | 0 | 0 | 0 |
| abuse_or_legal | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 3 |
| spam | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 |
| other | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |

## Routing at the dev-chosen tau

tau: 0.99

constraint met on dev: False

test coverage: 0.1264

test auto-routed error: 0.0000

test human-review share: 0.8736

accuracy: 0.7701

macro-F1: 0.7987
