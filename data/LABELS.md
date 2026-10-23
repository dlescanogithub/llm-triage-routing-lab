# How labels were produced

Labels on `data/golden.jsonl` and `data/adversarial.jsonl` were written with the text.

- Template rows (`tags` contains `template`) take the category of the template that generated them. The generator is `python -m triage_lab data generate --seed 7`.
- Authored rows (`tags` contains `authored`, 40 of them) were written one by one, including typos, informal wording, multi-intent, quoted threads, signature noise, and polite complaints that mention refunds. The label is the intent the author assigned, using the first real request when two intents appear.
- Adversarial attacks are labeled with the legitimate intent, not with the route the injected instruction asks for. `injection` is true on those rows. Benign look-alikes discuss the word "instructions" and have `injection` false.

These are not human annotations. There is no second annotator and no agreement statistic. The dev/test split is a hash of the id (`sha256(id) % 5 < 2` is dev) and is stored on each row. Thresholds are chosen on dev only.
