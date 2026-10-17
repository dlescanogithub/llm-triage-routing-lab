# ADR 0003: No refund, payment, or account tool

## Status

Accepted. 2026-10-17.

## Context

The risky action in support mail is not the label. It is a tool that moves money or changes an account while the model is still holding the customer's words.

## Decision

The registry in `src/triage_lab/tools.py` has four tools: `lookup_order_status`, `lookup_faq`, `create_ticket_note`, `route_to_queue`. Effects are read, note, or route. A test fails if any registered effect is a business write. `approve_refund` is not a tool. `compromised_sim` may ask for it; the allowlist blocks it, logs `tool_blocked`, and sends the ticket to `security_review`.

Credentials, when this is wired to a real read API, are separate and read-only per tool. No shared admin key. See `docs/RISKS.md`.

Refunds stay in another system after a person approves them.

## Consequences

Least privilege is structural. A prompt cannot approve a refund here because the function does not exist. The design boundary is documented so a later integration does not "just add" the tool to this process.
