# ADR 0001: CI providers are fakes

## Status

Accepted. 2026-10-17.

## Context

A portfolio lab needs a gate that runs without a key, a network, or a bill. Comparing two real models is a different activity.

## Decision

Ship deterministic profiles: `rules_baseline`, `small_sim`, `large_sim`, `cascade`, `naive_sim`, `compromised_sim`. `small_sim` and `large_sim` include configured error rates. Their accuracy is simulated by construction. The README states that fake-versus-fake numbers show the harness. Real-provider checks are recorded in `docs/LIVE_RUN_TEMPLATE.md`. CI still does not call them.

Cassette lookups miss closed. A missing entry raises. It does not call the network.

## Consequences

CI is stable and free. Nobody can cite `large_sim` accuracy as a model result. A live adapter exists and is tested with an injected transport. It is not part of the eval gate.
