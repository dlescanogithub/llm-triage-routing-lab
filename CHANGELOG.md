# Changelog

## 0.1.1 - 2026-10-22

- The repository is English. Shop tickets, templates, the FAQ reply, sanitizer markers, the keyword lexicon, fixtures, and docs are English. The small-sample rate label is `not conclusive`.
- Live accuracy and cost from 2026-10-17 stay as measured on the previous bilingual corpus. They were not re-run. Simulated profile figures were remeasured on the English corpus.
- Security reports go through GitHub private vulnerability reporting: open the Security tab and choose "Report a vulnerability".
- `docs/HOW_IT_WORKS.md` is a walkthrough for engineers and buyers. Interview-script framing is removed from that page and from the README docs index.
- `.gitleaksignore` lists the gitleaks fingerprints for the `secretscan.py` sha256 line in `docs/PROVENANCE.md`. That line is a digest. Gitleaks labels it `generic-api-key`.
- Translated the remaining Spanish documentation into English: `docs/HOW_IT_WORKS.md`, and leftover phrases in `docs/BUSINESS_CASE.md`, `docs/COST.md`, and `docs/LIVE_RUN_TEMPLATE.md`. Numbers, commands, links, and the labels `[EST]`, `[SYN]`, MEASURED, SIMULATED, and UNVERIFIED stay. `no concluyente` is now `not conclusive`.
- Expanded the English README to the same shape as the other portfolio labs: a three-line start, quickstart, use cases and governance, a short business-value section, a proof line, and what the lab does not prove.
- Added `docs/BUSINESS_VALUE.md`. Money figures are the ones already in `docs/BUSINESS_CASE.md` and `docs/COST.md`. No new rates.
- Refreshed `docs/HOW_IT_WORKS.md` so the walkthrough matches the gate, the demo, and the 2026-10-17 live record.
- Noted in `SECURITY.md` that CI does not enable live mode and does not build the image.

## 0.1.0

- Synthetic triage lab for Almacén Brújula: taxonomy, golden set, simulated profiles, invariant gate, shadow mode, and an optional live adapter that is off by default.
