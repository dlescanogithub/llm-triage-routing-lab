# Confusion matrix: small_sim

Generated: 2026-10-17 (UTC)

Command: `python -m triage_lab eval`

Package version: 0.1.0

Git commit: `81e3aac00afc5f3662fb20af60aa7642ba198a99`

Split: test

n: 87

Simulated profile. This matrix checks the comparison harness, not a real model.

| gold \\ pred | order_status | shipping_address_change | refund_request | payment_issue | product_question | complaint | abuse_or_legal | spam | other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| order_status | 8 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 1 |
| shipping_address_change | 0 | 4 | 0 | 0 | 1 | 0 | 0 | 0 | 3 |
| refund_request | 1 | 0 | 5 | 0 | 0 | 0 | 1 | 0 | 3 |
| payment_issue | 0 | 2 | 1 | 4 | 0 | 0 | 0 | 0 | 2 |
| product_question | 1 | 0 | 3 | 0 | 6 | 0 | 1 | 0 | 2 |
| complaint | 0 | 0 | 1 | 0 | 0 | 10 | 0 | 0 | 0 |
| abuse_or_legal | 0 | 0 | 0 | 0 | 1 | 0 | 6 | 0 | 3 |
| spam | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 |
| other | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 8 |

## Routing at the dev-chosen tau

tau: 0.99

constraint met on dev: False

test coverage: 0.1379

test auto-routed error: 0.1667

test human-review share: 0.8621

accuracy: 0.6437

macro-F1: 0.6646
