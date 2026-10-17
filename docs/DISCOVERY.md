# Discovery questions

Ten questions to ask before changing this lab into a deployment. Each answer moves a design choice.

1. **How many tickets per day, and what is the peak hour?**
   Volume sets the spend cap and whether a cascade is worth the second call. A few hundred a day can stay on a small profile plus human review. A spike changes `MAX_LIVE_SPEND_USD` and the monthly table in `docs/COST.md`.

2. **Who owns the category list, and how often does it change?**
   The owner of `data/taxonomy.yaml` is the only person who adds a category. Frequent changes mean you do not fine-tune; you version the YAML and retune tau on a fresh dev split.

3. **What is the SLA for a first route, and for a human reply?**
   A tight first-route SLA can justify auto-route on FAQ only. A tight human SLA means the human share is a staffing number, not only a safety number.

4. **Which languages must be correct on day one?**
   This lab is Spanish (rioplatense templates) and English. Another language is a new golden slice, not a prompt tweak. Coverage beyond es/en is design-only.

5. **What must never be automatic?**
   Here: refunds, payments, account changes, and any `injection=true` message (no `auto_reply_faq`). If the shop adds "address change must be human", `shipping_address_change` moves to `human_review` in the YAML.

6. **What counts as PII, and may it land in a log?**
   Traces in this lab keep ids and routes, not the full body. A real mailbox needs a redaction step before the provider. That service is design-only. The auto-reply text is a fixed FAQ string so the model cannot echo an order number.

7. **Which helpdesk is the system of record?**
   This repo does not call one. Shadow mode writes a report only. A webhook or IMAP ingest is design-only and stays outside the gate until the mapping of queues is signed.

8. **Who is on the escalation path for legal, abuse, and payment?**
   `abuse_or_legal` is hard-routed to `security_review`. Billing is a queue, not a refund tool. The named on-call is in `docs/RUNBOOK.md`.

9. **What error on auto-routed tickets is acceptable?**
   The lab uses 2% on the dev split (`TRIAGE_AUTO_ERROR_BUDGET`). A stricter number raises tau and the human share. Report the test number beside it; do not retune on test.

10. **Who may change tau, and who may turn the kill switch?**
    Tau is an approved config change. `FORCE_HUMAN_REVIEW=1` is an incident action: no provider call, every ticket to `human_review`. Write both names down before shadow traffic.
