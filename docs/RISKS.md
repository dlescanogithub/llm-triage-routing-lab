# Risks

Owners below are roles for the fictional shop, not a staffing chart.

| Risk | Probability | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| Prompt injection in the body changes the route or the tool | Medium on a real inbox; exercised here with `naive_sim` | High: refund or data echo | Known-marker sanitizer, data delimiters, I1–I4, allowlist, `security_review` | Security |
| Complaint or legal mail classified as FAQ | Medium | High: missed harm | `abuse_or_legal` ignores tau; complaints go to `support_queue`; auto-error budget 2% on dev | Support lead |
| Over-automation (tau too low) | Medium | Medium: bad replies at scale | Tau chosen on dev only; test reported separately; human share is a metric | Approver of tau |
| Taxonomy drift (new intents, old labels) | High after launch | Medium: silent accuracy drop | Version field in `data/taxonomy.yaml`; retune on a new dev split; no fine-tune in this repo | Taxonomy owner |
| Cost spike from retries or a cascade | Low in the lab; real if live is uncapped | Medium | `TRIAGE_MAX_ATTEMPTS`, token cap, `MAX_LIVE_SPEND_USD` reserved before each live call | Ops |
| PII in logs or auto-replies | Medium if a body is logged | High | Trace stores ids and routes; FAQ reply is a constant; no redaction service yet | Security |
| Benign mail over-blocked (talks about "instructions") | Medium if the marker list grows | Low to medium: extra human load | I7 budget 0.10; report benign over-block beside attack block rate | Eval owner |
| Compromised model calls a tool outside the route | Exercised by `compromised_sim` | High | Registry has no business-write tool; disallowed calls are logged and the ticket goes to `security_review` | Security |
| Kill switch unknown during an incident | Low | High | `FORCE_HUMAN_REVIEW=1` tested; runbook step | On-call |

## Credentials

Each tool is designed for its own read-only credential. There is no shared admin key in this process. `lookup_order_status` and `lookup_faq` read. `create_ticket_note` and `route_to_queue` write a note or a queue name inside the triage record, not a payment. Refunds are a different system. See `docs/adr/0003-no-refund-tool.md`.

## Known gap

The sanitizer neutralizes a fixed marker list (`src/triage_lab/sanitize.py`). A phrase that is not on that list is not flagged. Attack block rate 1.000 (n=22) is on the committed file, which uses that list. n=0 is reported as n/a.
