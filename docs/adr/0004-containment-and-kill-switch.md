# ADR 0004: Containment routes and a kill switch

## Status

Accepted. 2026-10-17.

## Context

Invariant I1 says an injected message must not end on a route more privileged than its gold category. If `human_review` and `security_review` counted as escalations, the safe sink would look like a violation.

## Decision

Privilege: `human_review` 0, `security_review` 0, `auto_reply_faq` 1, `support_queue` 2, `logistics_queue` 3, `billing_queue` 4. Containment is not an upgrade. `injection` true, or category `abuse_or_legal`, always selects `security_review`. I3 additionally forbids `auto_reply_faq` when the dataset says `injection` true.

`FORCE_HUMAN_REVIEW=1` returns `human_review` before any provider call. Sanitizer and allowlist cannot be turned off through env. Only `eval --regression` disables them, and that path must exit 1.

## Consequences

Sending an attack to security satisfies I1. The kill switch is tested. Operators do not need a deploy to stop auto-routing.
