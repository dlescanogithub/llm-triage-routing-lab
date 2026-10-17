# Prompting vs fine-tuning

Design only. No fine-tune was run. This document has no accuracy, no loss, and no cost for a trained model.

| Option | When it fits | Data volume | Label stability | Latency and cost per call | Drift | Governance | Label noise |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Instructions + schema, as this pipeline does | Categories are few and the risk is the route, not the wording | Small golden set is enough to gate | You can edit the YAML this week | One call, plus retries; cascade adds a second call | Change the prompt and retune tau | Text stays in the request you already send | A bad label moves tau, it is not baked into weights |
| Few-shot examples in the prompt | Edge cases are easier to show than to describe | Tens of examples | Stable enough to pin in the prompt | More input tokens every call | Swap examples, re-run the same gate | Examples may contain synthetic or real PII; redact first | A noisy example is copied every call |
| Retrieval of similar labeled tickets | The taxonomy is large and examples do not fit | Thousands, with a store | Index updates without a train job | Retrieval plus one call | Reindex | The store is another system to secure | Retrieved noise looks like evidence |
| Fine-tune | The schema is stable, volume is high, and prompt cost dominates | Enough fresh labels to hold out a test set you did not train on | Slow change; otherwise you retrain often | Cheaper or faster per call only if you measured it | A retrain schedule and a rollback model | Does customer text leave the org? Who owns the weights? | Noise becomes the model |
| Small classifier head on frozen embeddings | You want a calibrated score and a tiny artifact | Labeled rows, not chats | Same as fine-tune | Usually one forward pass | Retrain the head | Embeddings may still be a vendor call | Same holdout rule |

## When not to fine-tune

- The labels are template-generated, as in `data/LABELS.md`.
- The taxonomy still moves.
- You have not passed the invariant gate with a prompted model.
- The failure you care about is a tool call. Weights do not replace the allowlist.
- You cannot name who approves the training set and where it is stored.

## How this harness would evaluate a candidate

Design only:

1. Same `data/golden.jsonl` dev/test split. Tune tau on dev only.
2. Same adversarial file and invariants I1–I7. The gate must exit 0.
3. Same forced-regression idea: a build that disables the sanitizer must still fail closed in CI, so the candidate cannot "pass" by skipping controls.
4. Shadow, then a canary on FAQ only.
5. Rollback is the previous prompt or the previous model name, plus `FORCE_HUMAN_REVIEW=1` if the canary misroutes.

`python -m triage_lab data export-sft` writes a chat-format JSONL of the dev split on local disk. It does not upload and it does not train. That command is illustration, not a training pipeline.
