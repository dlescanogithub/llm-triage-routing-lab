# Provenance

Small utilities in this repository follow patterns used across the portfolio and are maintained in parallel with the other portfolio repos, kept aligned by hand: the cassette provider, invariant checks, the JSONL trace, structured logging, and `secretscan.py`.

The cassette returns a scripted completion keyed by a hash of the normalized request. A missing entry is an error. Invariant checks read a trace and return violations. The trace is one JSON object per line (`run_id`, `ts`, `kind`, `payload`) and does not store secrets. The log formatter emits `ts`, `level`, `msg`, and `run_id`, and redacts secret-shaped strings.

What this repo adds on top of those utilities is the ticket taxonomy, the threshold policy, the simulated classifier profiles, the shadow report, and the optional live adapter.

All ticket text, names, order numbers, and shop details are synthetic. Nothing is copied from employer or client work.

secretscan.py sha256: 2cdf0339ef5a85d4f6439e94c973b5858375f9da0e2d38da9b503e06d0f6dff7
