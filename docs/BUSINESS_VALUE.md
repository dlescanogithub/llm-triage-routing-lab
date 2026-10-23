# Business value: adopting this triage lab

> **Notice**
>
> - The shop in this repository, Almacén Brújula, is fictional. It is not an employer and not a client. Order numbers and mailboxes in the data files are synthetic.
> - This plan reuses [docs/BUSINESS_CASE.md](BUSINESS_CASE.md), [docs/COST.md](COST.md), [docs/METRICS.md](METRICS.md), and [docs/SCOPE.md](SCOPE.md). It does not add money figures. Where a cell would need a new assumption, the cell says the repo does not record it.
> - Tags used here:
>   - **MEASURED**: a command in this repo, or a live check recorded in [docs/LIVE_RUN_TEMPLATE.md](LIVE_RUN_TEMPLATE.md), with the date.
>   - **[EST]**: a placeholder the existing business and cost notes already mark as illustrative.
>   - **SIMULATED**: a fake profile whose errors are configured, or a token count from the character heuristic.
>   - **UNVERIFIED**: a live or business claim this repo does not store enough evidence to close.
> - No **[SYN]** figure is introduced. The sibling labs use that tag for invented volumes and rates. This repo already has its own [EST] volume table, and this file stays inside it.
> - Package 0.1.0. Eval and cost figures below are the 2026-10-17 run (`python -m triage_lab eval`). The cost write-up names commit `d5f1a0ec694a34dd2977db170820abf25f9ddb06`. The invariant summary names commit `81e3aac00afc5f3662fb20af60aa7642ba198a99`. The unit-test line is **MEASURED** 2026-10-22, Python 3.12.3, pytest 9.1.1: 77 passed, pytest-cov total 91.38 percent. See the README section "Proof".

## Buyer and problem

The buyer for this lab is the owner of one support inbox at the fictional shop. The inbox is Spanish and English, nine categories, six routes ([docs/SCOPE.md](SCOPE.md)).

Today the baseline is all-human triage ([docs/BUSINESS_CASE.md](BUSINESS_CASE.md)). Two costs sit on that baseline, both placeholders:

- Handling time **[EST] 4 minutes** per ticket at **[EST] USD 15 per hour**, which the notes reduce to **[EST] USD 1.00 per ticket**.
- A misrouted auto-reply, separate from handling time: **[EST] USD 8.00** per misroute (goodwill plus a second touch).

The failure the lab is built to show is not "the model was inaccurate." It is a classifier that can be talked into a refund or an auto-reply. Refunds, charges, and account edits stay in another system. This service has no refund tool ([docs/adr/0003-no-refund-tool.md](adr/0003-no-refund-tool.md)).

The repo does not record a real ticket volume, a real wage, a real misroute count, or a contract. The 1,000 / 10,000 / 50,000 tickets-per-month rows in [docs/COST.md](COST.md) are a sensitivity table, "an illustration of staffing, not a forecast."

## Value levers

Four levers, in the order the cost notes say they matter.

1. **Human share.** Blended cost is almost entirely the human placeholder. Token price does not decide the case until the share of tickets that still need a person drops ([docs/COST.md](COST.md)). On the 2026-10-17 `large_sim` draw the dev constraint (auto-routed error at or below 2 percent) forces tau 0.90 and still leaves a test human share of 0.5977. That share is **SIMULATED**.
2. **Auto-route errors, kept small.** The gate's job is to keep the misroute term small. The worked illustration in the business case: if auto-error were 2 percent on a 40 percent auto-route share, misroute would add 0.40 times 0.02 times 8.00 = **0.064 USD per ticket [EST]**. `large_sim` and `cascade` had test auto-error 0 on the auto-routed slice of that run. `rules_baseline` and `small_sim` did not meet the dev constraint at any tau. Their reported tau is 0.99. Do not treat their blended saving as an approved operating point.
3. **Token spend.** At the placeholder prices this is cents per thousand tickets. It is real arithmetic on simulated tokens, and it is not a vendor invoice. The estimate ignores cached tokens.
4. **Containment.** Known-marker injection goes to `security_review`. `abuse_or_legal` ignores tau. `FORCE_HUMAN_REVIEW` set to 1 skips the provider. The repo does not put a dollar figure on a fraud loss avoided. The control is the point of the gate; the [EST] saving above does not include a fraud term.

`large_sim` test accuracy 0.9655 is **SIMULATED** by construction. The business case says not to put that accuracy into the saving formula.

## Baseline and target KPIs

"Target" below is a threshold this repo already states (an exit criterion, a budget, or a constraint). Where the repo states no target, the cell says so. It does not borrow one.

| KPI | Category | Baseline | Target | How it is measured here | Label |
| --- | --- | --- | --- | --- | --- |
| Invariant failures on `python -m triage_lab eval` | Operational resilience | 0 failures on 2026-10-17. I1–I6: 34 pass and 0 fail. I7: 1 pass and 0 fail | Exit 0 on the committed adversarial file ([docs/SCOPE.md](SCOPE.md)) | Eval command, exit code, counts in [docs/results/summary.json](results/summary.json) | MEASURED |
| Forced regression | Operational resilience | Exit 1. I1 is 18 pass and 14 fail, I2 is 24 pass and 8 fail, I3 is 27 pass and 5 fail. Attack block prints as 0.091 on 22 messages (2 of 22) | Must stay exit 1. Exit 0 means the gate is broken | `python -m triage_lab eval --regression` | MEASURED |
| Attack block on the known-marker file | Risk | 1.000 on 22 messages | The gate on that file. No field-rate target is stated | `data/adversarial.jsonl`, slice `attack` | MEASURED on the synthetic file. UNVERIFIED on any other attack text |
| Benign over-block | Experience | 0.000 on 10 messages | Budget 0.10 (I7, [docs/METRICS.md](METRICS.md)) | Slice `benign_lookalike` | MEASURED on 10 synthetic look-alikes |
| Dev auto-error | Quality of the route | `large_sim` and `cascade` met the cap on this draw. `rules_baseline` and `small_sim` did not | At or below 0.02 on the dev split. Tau is frozen before test | `select_tau` on dev, then report test | SIMULATED profiles |
| Test human share | Productivity | All-human share is 1, by the [EST] baseline | No numeric target in the repo. Reported `large_sim` test share is 0.5977. `cascade` is 0.8276 | Test split of the named eval | SIMULATED. The all-human 1 is the [EST] baseline, not a count of staff |
| Test auto-error among auto-routed | Quality | `large_sim` 0 of 35. `cascade` 0 of 15. `rules_baseline` 0 of 11 at tau 0.99, constraint not met. `small_sim` 2 of 12 | Reported, not tuned. The cap is the dev cap above | Same eval | SIMULATED |
| Blended USD per ticket | Cost | 1.00 all-human [EST] | No target price. `large_sim` blended is 0.599 [EST] on this draw | Formula in the ROI section | [EST], using SIMULATED tokens and route shares |
| Live schema-valid and category accuracy | Quality | 2026-10-17, one model, 87 messages: schema-valid 87 of 87; accuracy 82 of 87 and 83 of 87. The notes state that 83 of 87 is 95.4 percent | No launch target. The README says not to treat this sample as a launch metric | [docs/LIVE_RUN_TEMPLATE.md](LIVE_RUN_TEMPLATE.md) | MEASURED, small sample. UNVERIFIED as a rate you could staff to |
| Live attack block | Risk | 4 messages, inconclusive. Benign over-block not applicable (0 messages) | A count from 1 to 4 is not reported as a rate ([docs/METRICS.md](METRICS.md)) | Same template | MEASURED count, inconclusive rate |
| Time to route | Experience | Not measured. The eval clock is frozen | Left blank | [docs/METRICS.md](METRICS.md) | Not measured |
| Handle minutes | Productivity | 4 minutes [EST] | No measured target. The notes do not claim the person becomes faster, only that some tickets might leave the queue | Not measured in this repo | [EST] input |
| Unit tests and line coverage | Engineering | Floor 80 percent in `pyproject.toml` | At or above 80 percent ([docs/SCOPE.md](SCOPE.md)) | `python -m pytest` with the coverage flags in `addopts` | MEASURED 2026-10-22: 77 passed, 91.38 percent, Python 3.12.3 |

A denominator of 0 is not a rate of 0. The 2026-10-17 live benign over-block is the example: 0 messages, so the rate is not applicable.

## ROI model

The repo's formula ([docs/BUSINESS_CASE.md](BUSINESS_CASE.md)), not a return on an implementation budget:

```
model_usd = (tokens_in / 1e6) * price_in + (tokens_out / 1e6) * price_out
blended_usd = model_usd + human_share * human_usd + auto_error * misroute_usd
saving_usd = human_usd - blended_usd
```

### Assumptions, all already marked [EST] in the source notes

| Input | Value | Source |
| --- | --- | --- |
| Handling time | 4 minutes per ticket | [docs/BUSINESS_CASE.md](BUSINESS_CASE.md) |
| Loaded rate | USD 15 per hour | same |
| Human cost | USD 1.00 per ticket | 4 / 60 times 15, as the notes state it |
| Misroute cost | USD 8.00 per misrouted auto-reply | same |
| Input price | USD 1.00 per million tokens | [docs/COST.md](COST.md). Not a vendor card |
| Output price | USD 3.00 per million tokens | same |
| Cached-token discount | None. The estimate ignores cached tokens | same |

Prices are described as "chosen for arithmetic." Date of the token measurement: 2026-10-17.

### Worked example, `large_sim`, that same run

Copied from the business case. Tokens are simulated.

- Simulated tokens 989.207 in and 130 out per ticket.
- `model_usd` = 0.001379.
- Test human share 0.5977. Auto-error among auto-routed = 0.0000 (0 of 35).
- `blended_usd` = 0.001379 + 0.5977 times 1.00 + 0 = **0.599 [EST]**.
- Saving versus all-human = **0.401 USD per ticket [EST]**.

`cascade` on the same draw meets the dev constraint at tau 0.95, with test human share 0.8276 and blended **0.830 [EST]** ([docs/COST.md](COST.md)). Saving versus USD 1.00 is 0.170 per ticket by the same formula. The cascade still sends most tickets to a person, so the saving is smaller. Tokens 1498.414 in and 210 out are simulated and include both calls.

`rules_baseline` blended 0.874 and `small_sim` blended 0.863 are printed in the cost note and are **not** approved operating points. The dev constraint was not met.

### What this model is, and what it is not

An investment ROI of the form (benefit minus cost) divided by cost, and a payback in months, need an implementation cost. This repo does not record build hours, an engineering rate, a vendor minimum, or a telephony or helpdesk fee. Those payback months are **not calculated**. Inventing an hour count would contradict the cost note.

The operating difference at a flat volume is arithmetic on the [EST] saving, using the volume rows the cost note already publishes. It is not a forecast. For `large_sim` at 0.401 USD per ticket:

| Tickets in the month (published illustration) | All-human USD [EST] | `large_sim` blended USD [EST], from the cost table | Operating difference USD [EST] |
| --- | ---: | ---: | ---: |
| 1,000 | 1,000 | 599 | 401 |
| 10,000 | 10,000 | 5,990 | 4,010 |
| 50,000 | 50,000 | 29,950 | 20,050 |

Check: 1,000 times 0.401 = 401, and 1,000 minus 599 = 401. The same identity holds on the other two rows (10,000 times 0.401 = 4,010; 50,000 times 0.401 = 20,050).

If someone divides that difference by the blended cost, the ratio is 0.401 / 0.599 on every row, about **66.9 percent**. That ratio is [EST] arithmetic. It is not a project ROI. It shrinks if a person still re-reads every auto-routed ticket, because the human share would then be higher than 0.5977. The repo does not measure that re-read. [docs/BUSINESS_CASE.md](BUSINESS_CASE.md) already warns that the saving is only as good as the human share.

The 2026-10-17 live bill (last run US$0.0391, repo estimate 0.0675 ignoring cached tokens) is **not** this [EST] saving. The business case says the [EST] saving still uses simulated tokens and a placeholder human cost.

## Cost table

Providers in the profile rows are simulated. Accuracy in those rows is not a model measurement. Latency is not measured. Prices are the [EST] placeholders above. Arithmetic: `(tokens_in * 1.00 + tokens_out * 3.00) / 1e6`. Source: [docs/COST.md](COST.md), run date 2026-10-17, package 0.1.0.

| Scenario | Tokens in/out per ticket (simulated) | USD per ticket [EST] | USD per 1,000 [EST] | Test human share | Blended USD per ticket [EST] | Dev constraint |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| rules_baseline | 357.207 / 36 | 0.000465 | 0.465 | 0.8736 | 0.874 | not met |
| small_sim | 509.207 / 80 | 0.000749 | 0.749 | 0.8621 | 0.863 | not met |
| large_sim | 989.207 / 130 | 0.001379 | 1.379 | 0.5977 | 0.599 | met |
| cascade | 1498.414 / 210 | 0.002128 | 2.128 | 0.8276 | 0.830 | met |
| live, `grok-4.20-0309-non-reasoning` | not stored | not measured as a per-ticket [EST] row | not measured | not in this table | not in this table | not applicable |

The live row is **MEASURED** as a run, not as a price card: schema-valid 87 of 87, accuracy 82 of 87 and 83 of 87, last run US$0.0391, repo estimate 0.0675 ignoring cached tokens. Attack block on that split is inconclusive (4 messages). Benign over-block is not applicable (0 messages). An earlier same-day check was 0 of 40 schema-valid because the prompt lacked the taxonomy. That prompt was corrected.

### Monthly model cost and the `large_sim` blended illustration

Copied from [docs/COST.md](COST.md). The blended column uses only the `large_sim` figure, as an illustration of staffing, not as a forecast. Model columns are the per-ticket [EST] cost times the volume.

| Tickets in the month | rules model USD [EST] | large model USD [EST] | cascade model USD [EST] | large blended USD [EST] |
| --- | ---: | ---: | ---: | ---: |
| 1,000 | 0.47 | 1.38 | 2.13 | 599 |
| 10,000 | 4.65 | 13.79 | 21.28 | 5,990 |
| 50,000 | 23.26 | 68.96 | 106.42 | 29,950 |

A comparative live check that used one price for every model recorded 0.0044 USD for `grok-4.3` against about 0.0131 USD at that model's own rate (2026-10-17, reported from the run, not recomputed here). A missing row in `LLM_MODEL_PRICE_TABLE` aborts before the call.

There is no row in this repo for integration cost, shadow staffing, or a monthly platform fee. Those cells are omitted rather than filled.

## Measurement plan

Phases are the ones in [docs/SCOPE.md](SCOPE.md). Phases 1 through 4 are not done. Phase 0 is this lab.

| Phase | What is measured | Exit, as the scope note states it | Status |
| --- | --- | --- | --- |
| 0. Lab | Invariant gate, forced regression, tests and the coverage floor | Eval exits 0. Regression exits 1. Coverage of `triage_lab` at or above 80 percent. A reader can tell simulated scores from the control measurement | This repo. Gate and regression recorded 2026-10-17. Coverage **MEASURED** 2026-10-22 at 91.38 percent on Python 3.12.3 |
| 1. Shadow on a real export | Routes and human share. No customer effect | A report of routes and human share. No tool side effects | Not done. The local command is `python -m triage_lab shadow`. It does not read a mailbox |
| 2. Capped live comparison | Date, model, command, cost, message count, attack block, benign over-block | A filled row in [docs/LIVE_RUN_TEMPLATE.md](LIVE_RUN_TEMPLATE.md). Token cells stay empty when the run did not store them | One model, 2026-10-17, is filled. Tokens for the 87-message runs are empty on purpose. Not in CI |
| 3. Limited auto-reply | Auto-error on a fresh labeled sample, FAQ route only, kill switch rehearsed | Auto-error within the agreed budget | Not done |
| 4. Queue assist | Read-only lookups on logistics and billing | Still no refund tool in this service | Not done |

What a later measurement has to bring, because this repo does not have it:

- A handle time sampled on real tickets. Until then the 4 minutes stay [EST].
- A wage that is not the USD 15 placeholder.
- Attack text that is not on the marker list, with a denominator above 4 before a rate is quoted.
- A second annotator, if the labels are going to be cited as human labels. [data/LABELS.md](../data/LABELS.md) says these labels are not that.
- Latency. The eval clock is frozen. A fake clock is not a p50.
- The Python 3.11 coverage number. CI runs 3.11. This file reports 3.12.3 only.

Live mode refuses to start without `LIVE_LLM` set to 1 and `MAX_LIVE_SPEND_USD` greater than zero. A missing model price aborts before the HTTP call. That is a spend control, not a quality measurement.

## Risks

Owners are roles for the fictional shop, copied from [docs/RISKS.md](RISKS.md). Probability and impact there are qualitative. This table does not add scores.

| Risk | What the risk note says | What this lab already does | What is still open |
| --- | --- | --- | --- |
| Prompt injection changes the route or the tool | Medium on a real inbox; exercised here with `naive_sim`. Impact high | Known-marker sanitizer, delimiters, I1–I4, allowlist, `security_review` | The list is fixed. Unknown phrasing is not flagged. Owner: security |
| Complaint or legal mail classified as FAQ | Medium, impact high | `abuse_or_legal` ignores tau. Complaints go to `support_queue`. Dev auto-error budget 2 percent | Owner: support lead. Not measured on a live queue |
| Tau too low | Medium | Tau chosen on dev only. Test is reported, not used to retune | Owner: the person who approves tau |
| Taxonomy drift | High after a launch, impact medium | Version field in `data/taxonomy.yaml`. No fine-tune in this repo | Needs a new dev split when the list changes. Owner: taxonomy owner |
| Cost spike from retries or a cascade | Low in the lab | Attempt cap, token cap, spend cap reserved before each live call | Owner: ops. The cap is not a measured bill |
| PII in logs or auto-replies | Medium if a body is logged, impact high | Trace stores ids and routes. FAQ reply is a constant | No redaction service. Owner: security |
| Benign mail over-blocked | Medium if the marker list grows | I7 budget 0.10. The lab file is 0.000 on 10 messages | A longer list can move this. Owner: eval owner |
| Compromised model calls a tool outside the route | Exercised by `compromised_sim` | Registry has no business-write tool. Disallowed calls are logged and the ticket goes to `security_review` | Owner: security |
| Kill switch unknown during an incident | Low probability, high impact | `FORCE_HUMAN_REVIEW` set to 1 is tested. Runbook step | Someone has to be named before shadow traffic ([docs/DISCOVERY.md](DISCOVERY.md)) |

The regression shows the gate can see a broken sanitizer: with the sanitizer and the allowlist off, `naive_sim` fails I1, I2, and I3 and the process exits 1. That is the control. It is not a measurement of a model that behaves.

## Measured and not measured

**MEASURED**

- 2026-10-22, Python 3.12.3, pytest 9.1.1, package 0.1.0: 77 passed, pytest-cov total coverage 91.38 percent. The table rounds the same total to 91 percent (2019 statements, 174 missed). The run printed a coverage warning that `triage_lab` was imported before measurement. The 91.38 percent figure is the total line anyway. Command and the warning text are in the README section "Proof".
- 2026-10-17 eval gate: 0 invariant failures. Attack block 1.000 on 22 messages. Benign over-block 0.000 on 10 messages. I1–I6 on 34 messages (32 adversarial rows plus two probes).
- 2026-10-17 forced regression: exit 1, with the pass/fail counts in the KPI table.
- 2026-10-17 live check, `grok-4.20-0309-non-reasoning`, temperature 0, test split: schema-valid 87 of 87; accuracy 82 of 87 and 83 of 87; last run US$0.0391; repo estimate 0.0675 ignores cached tokens. The template calls this measured by independent verification. Attack messages: 4, inconclusive. Benign messages: 0, rate not applicable.
- 2026-10-17 earlier live check: 0 of 40 schema-valid, prompt without the taxonomy, later corrected. Kept so the corrected run is not confused with it.
- Demo stdout on 2026-10-22, `large_sim`, three lines: product question to `auto_reply_faq`, order status to `logistics_queue`, known-marker injection to `security_review`. Recorded in the README quickstart.

**SIMULATED**

- Accuracy, macro-F1, ECE, coverage, human share, and auto-error for `rules_baseline`, `small_sim`, `large_sim`, and `cascade`.
- Token counts (character heuristic plus profile overhead).
- McNemar on those fakes (32, 21, and 11 discordant pairs). A comparison of fakes, not of models.

**[EST]**

- USD 1.00 per ticket, USD 15 per hour, 4 minutes, USD 8.00 per misroute.
- USD 1.00 and USD 3.00 per million tokens, and every blended and monthly dollar figure derived from them.
- The 0.401 USD per ticket saving and the 401 / 4,010 / 20,050 operating differences.

**Not measured, or UNVERIFIED as a business result**

- Latency, including any p50 or p95. The eval clock is frozen.
- Live token counts for the 87-message runs. The template leaves them empty.
- Whether a person actually spends 4 minutes, or re-checks the auto-routed slice.
- A live inbox attack rate. Four messages is not a rate.
- Annotator agreement.
- Coverage on Python 3.11, even though CI runs that version.
- Any dollar outcome on a real queue. The [EST] table is not that outcome.
- Fine-tuning. [docs/PROMPTING_VS_FINETUNING.md](PROMPTING_VS_FINETUNING.md) is design only and states that it has no accuracy, no loss, and no cost for a trained model.

The robust value this lab can defend is the control: a route decision with a threshold, a human fallback, a tool allowlist, a known-marker sanitizer, and a kill switch that skips the provider. The dollar saving is [EST] and moves with the human share.
