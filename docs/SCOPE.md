# Scope

No fees. The shop, the tickets, and the order numbers (`AB-000123`) are synthetic.

## Assumptions

- One inbox, two languages (es, en), nine categories, six routes.
- The classifier returns a schema. It does not send mail except through the fixed FAQ string after `auto_reply_faq`.
- Refunds, charges, and account edits happen in another system after a person approves them.
- Thresholds are fit on `split=dev` only.
- CI runs fakes. A live model is opt-in and capped.

## Phases

| Phase | What happens | Exit criteria |
| --- | --- | --- |
| 0. Lab (this repo) | Golden set, fakes, invariant gate, shadow | Gate exit 0; forced regression exit 1; tests and coverage floor |
| 1. Shadow on a real export | Same pipeline, dry-run, no customer effect | Report of routes and human share; no tool side effects |
| 2. Capped live comparison | `LIVE_LLM=1`, ledger under `var/live-evals/` | Table filled in `docs/LIVE_RUN_TEMPLATE.md` with date, model, command, cost, n |
| 3. Limited auto-reply | FAQ route only, kill switch rehearsed | Auto-error within the agreed budget on a fresh labeled sample |
| 4. Queue assist | Logistics and billing queues get read-only lookups | Still no refund tool in this service |

Phases 1–4 are not done. Phase 0 is the implemented lab.

## Out of scope

Fine-tuning, IMAP or webhook ingest, helpdesk connectors, SSO/RBAC, languages besides es/en, production drift monitors, a PII redaction service, and any write to a payment or account system.

## Exit criteria for the lab

- `python -m triage_lab eval` exits 0 with zero invariant failures on the committed adversarial file.
- `python -m triage_lab eval --regression` exits 1 because I1, I2, and I3 fail.
- Pytest coverage of `triage_lab` stays at or above 80%.
- A reader can tell simulated profile scores from the control measurement.
