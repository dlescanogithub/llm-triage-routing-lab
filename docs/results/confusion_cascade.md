# Confusion matrix: cascade

Generated: 2026-10-17 (UTC)

Command: `python -m triage_lab eval`

Package version: 0.1.0

Git commit: `81e3aac00afc5f3662fb20af60aa7642ba198a99`

Split: test

n: 87

Simulated profile. This matrix checks the comparison harness, not a real model.

| gold \\ pred | order_status | shipping_address_change | refund_request | payment_issue | product_question | complaint | abuse_or_legal | spam | other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| order_status | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| shipping_address_change | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| refund_request | 1 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 |
| payment_issue | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 1 |
| product_question | 0 | 0 | 0 | 0 | 13 | 0 | 0 | 0 | 0 |
| complaint | 0 | 0 | 0 | 0 | 0 | 11 | 0 | 0 | 0 |
| abuse_or_legal | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 | 0 |
| spam | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 |
| other | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 8 |

## Routing at the dev-chosen tau

tau: 0.95

constraint met on dev: True

test coverage: 0.1724

test auto-routed error: 0.0000

test human-review share: 0.8276

accuracy: 0.9655

macro-F1: 0.9667
