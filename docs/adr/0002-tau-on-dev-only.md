# ADR 0002: Choose tau on dev, report test

## Status

Accepted. 2026-10-17.

## Context

A threshold fit on the same rows you publish will look safer than it is. The split is stored on each golden row so it cannot drift between runs.

## Decision

Dev is `sha256(id)` prefix mod 5 in {0, 1} (63 of 150 rows at seed 7). Pick tau to maximize dev coverage with auto-routed category error <= 2%. Tie-break: higher tau. If no tau qualifies, report 0.99 and `dev_constraint_met=false`. Publish test coverage, test auto-error, and human share at that frozen tau.

Auto-routed means the route is not `human_review`. `security_review` counts as auto-routed for the error rate, so abuse mistakes are not hidden by the threshold.

## Consequences

`rules_baseline` and `small_sim` honestly fail the constraint. `large_sim` can meet it partly because low-confidence flips fall below tau. That is a property of the fake, called out in `docs/METRICS.md`.
