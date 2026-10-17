"""Environment-only settings. Defaults keep live mode off."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PipelineConfig:
    tau: float = 0.8
    max_attempts: int = 3
    backoff_cap_s: float = 0.05
    max_tokens_per_ticket: int = 8000
    sanitize: bool = True
    allowlist: bool = True
    kill_switch: bool = False
    dry_run: bool = False
    benign_fp_budget: float = 0.10
    auto_error_budget: float = 0.02

    def replace(self, **changes: Any) -> PipelineConfig:
        from dataclasses import replace as replace_dataclass

        updated = replace_dataclass(self, **changes)
        if not isinstance(updated, PipelineConfig):
            raise TypeError("replace returned an unexpected type")
        return updated


def repo_root() -> Path:
    """Repository root, found by walking up to ``pyproject.toml``."""
    start = Path(__file__).resolve()
    for parent in start.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return Path.cwd()


def data_dir() -> Path:
    """Directory with taxonomy YAML and JSONL sets."""
    override = os.environ.get("TRIAGE_DATA_DIR", "").strip()
    if override:
        return Path(override)
    start = Path(__file__).resolve()
    for parent in start.parents:
        candidate = parent / "data" / "taxonomy.yaml"
        if candidate.is_file():
            return candidate.parent
    return Path("data")


def _env_map(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if env is None:
        return os.environ
    return env


def _optional_float(env: Mapping[str, str], name: str) -> float | None:
    raw = env.get(name, "").strip()
    if not raw:
        return None
    return float(raw)


def pipeline_config_from_env(env: Mapping[str, str] | None = None) -> PipelineConfig:
    """Build the safe pipeline config. Sanitizer and allowlist stay on."""
    source = _env_map(env)
    tau = _optional_float(source, "TRIAGE_TAU")
    max_attempts = source.get("TRIAGE_MAX_ATTEMPTS", "").strip()
    backoff = source.get("TRIAGE_BACKOFF_CAP_S", "").strip()
    token_cap = source.get("TRIAGE_MAX_TOKENS_PER_TICKET", "").strip()
    fp_budget = source.get("TRIAGE_BENIGN_FP_BUDGET", "").strip()
    error_budget = source.get("TRIAGE_AUTO_ERROR_BUDGET", "").strip()
    return PipelineConfig(
        tau=0.8 if tau is None else tau,
        max_attempts=int(max_attempts) if max_attempts else 3,
        backoff_cap_s=float(backoff) if backoff else 0.05,
        max_tokens_per_ticket=int(token_cap) if token_cap else 8000,
        sanitize=True,
        allowlist=True,
        kill_switch=source.get("FORCE_HUMAN_REVIEW", "0").strip() == "1",
        dry_run=False,
        benign_fp_budget=float(fp_budget) if fp_budget else 0.10,
        auto_error_budget=float(error_budget) if error_budget else 0.02,
    )


def tau_override(env: Mapping[str, str] | None = None) -> float | None:
    """Return TRIAGE_TAU when the operator pins it, else None (tune on dev)."""
    return _optional_float(_env_map(env), "TRIAGE_TAU")
