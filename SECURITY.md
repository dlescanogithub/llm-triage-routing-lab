# Security

This repository is a synthetic lab. It does not connect to a helpdesk, a mailbox, or a payment system.

## Reporting

Open a private security advisory on this repository. Do not paste live API keys, mailbox dumps, or customer data into issues or pull requests.

## What the lab enforces

- Tools are read or queue bookkeeping. There is no refund, payment, or account tool.
- A known-marker sanitizer and a route allowlist sit in front of the classifier.
- `FORCE_HUMAN_REVIEW=1` sends every ticket to `human_review`.
- Live mode is off unless `LIVE_LLM=1`, and it refuses to start without `MAX_LIVE_SPEND_USD` greater than zero.
- Logs and traces are redacted for credential-shaped strings. The live API key is registered for redaction and is not written to the ledger.

## Limits

The sanitizer only neutralizes a fixed marker list. It is not a general injection detector. See `docs/RISKS.md`.
