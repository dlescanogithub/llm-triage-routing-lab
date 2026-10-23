# Number trace — llm-triage-routing-lab demo
| On screen / spoken | Value | Kind | Source |
| --- | --- | --- | --- |
| demo-1/2/3 routes | FAQ / logistics / security_review | MEASURED script | `triage_lab demo` |
| I1–I7 | all pass | MEASURED | `triage_lab eval` |
| attack_block_rate | 1.000 (n=22) | MEASURED | eval stdout |
| benign_overblock_rate | 0.000 (n=10) | MEASURED | eval stdout |
| cascade accuracy | 0.9655 | SIMULATED (fake providers) | eval METRIC cascade |
| regression attack block | ~0.091 | MEASURED | `eval --regression` (exit 1) |
| Lab path cost | US$0 | MEASURED | offline |
