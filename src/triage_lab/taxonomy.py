"""Versioned category, route and tool policy loaded from YAML."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from triage_lab.config import data_dir


@dataclass(frozen=True)
class Taxonomy:
    version: int
    categories: tuple[str, ...]
    routes: tuple[str, ...]
    category_route: Mapping[str, str]
    privilege: Mapping[str, int]
    containment_routes: frozenset[str]
    route_tools: Mapping[str, tuple[str, ...]]
    category_tools: Mapping[str, tuple[str, ...]]

    def route_for(self, category: str) -> str:
        return self.category_route[category]

    def privilege_of(self, route: str) -> int:
        return self.privilege[route]

    def is_containment(self, route: str) -> bool:
        return route in self.containment_routes


def load_taxonomy(path: Path | None = None) -> Taxonomy:
    target = path if path is not None else data_dir() / "taxonomy.yaml"
    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("taxonomy YAML must be a mapping")
    return _parse(loaded)


def _as_str_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    return tuple(value)


def _as_mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping")
    return value


def _parse(raw: Mapping[str, Any]) -> Taxonomy:
    categories = _as_str_tuple(raw.get("categories"), "categories")
    routes = _as_str_tuple(raw.get("routes"), "routes")
    category_route_raw = _as_mapping(raw.get("category_route"), "category_route")
    privilege_raw = _as_mapping(raw.get("privilege"), "privilege")
    containment = frozenset(
        _as_str_tuple(raw.get("containment_routes"), "containment_routes")
    )
    route_tools = _tool_table(_as_mapping(raw.get("route_tools"), "route_tools"))
    category_tools = _tool_table(
        _as_mapping(raw.get("category_tools"), "category_tools")
    )
    category_route = {
        str(key): _require_str(value) for key, value in category_route_raw.items()
    }
    privilege: dict[str, int] = {}
    for key, value in privilege_raw.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"privilege for {key} must be an int")
        privilege[str(key)] = value
    version = raw.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise ValueError("version must be an int")
    _validate(
        categories,
        routes,
        category_route,
        privilege,
        containment,
        route_tools,
        category_tools,
    )
    return Taxonomy(
        version=version,
        categories=categories,
        routes=routes,
        category_route=category_route,
        privilege=privilege,
        containment_routes=containment,
        route_tools=route_tools,
        category_tools=category_tools,
    )


def _require_str(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("expected a string")
    return value


def _tool_table(raw: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    table: dict[str, tuple[str, ...]] = {}
    for key, value in raw.items():
        table[str(key)] = _as_str_tuple(value, f"tools for {key}")
    return table


def _validate(
    categories: tuple[str, ...],
    routes: tuple[str, ...],
    category_route: Mapping[str, str],
    privilege: Mapping[str, int],
    containment: frozenset[str],
    route_tools: Mapping[str, tuple[str, ...]],
    category_tools: Mapping[str, tuple[str, ...]],
) -> None:
    if set(category_route) != set(categories):
        raise ValueError("category_route must cover every category exactly once")
    if set(privilege) != set(routes):
        raise ValueError("privilege must cover every route")
    if set(route_tools) != set(routes):
        raise ValueError("route_tools must cover every route")
    if set(category_tools) != set(categories):
        raise ValueError("category_tools must cover every category")
    unknown_routes = set(category_route.values()) - set(routes)
    if unknown_routes:
        raise ValueError(f"unknown routes in category_route: {sorted(unknown_routes)}")
    if not containment <= set(routes):
        raise ValueError("containment_routes must be a subset of routes")
    for category, route in category_route.items():
        if category_tools[category] != route_tools[route]:
            raise ValueError(f"category tools for {category} must match route {route}")
