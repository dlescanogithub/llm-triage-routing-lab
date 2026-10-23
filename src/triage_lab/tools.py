"""Least-privilege tool registry.

The four tools are read or queue bookkeeping. There is no refund, payment or
account tool in this service. Those effects belong to another system after a
person approves them.
"""

from __future__ import annotations

from dataclasses import dataclass

FAQ_REPLY = (
    "Thanks for writing to Almacén Brújula. "
    "Sizes and care are on the product page. "
    "If a detail is missing, a person on the team fills it in."
)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    effect: str
    description: str


REGISTRY: dict[str, ToolSpec] = {
    "lookup_order_status": ToolSpec(
        name="lookup_order_status",
        effect="read",
        description="Read a synthetic order status. Does not change the order.",
    ),
    "lookup_faq": ToolSpec(
        name="lookup_faq",
        effect="read",
        description="Read a canned product-care answer. Does not send mail by itself.",
    ),
    "create_ticket_note": ToolSpec(
        name="create_ticket_note",
        effect="note",
        description="Attach an internal note for the queue. Not a customer write.",
    ),
    "route_to_queue": ToolSpec(
        name="route_to_queue",
        effect="route",
        description="Record the chosen queue name. Does not execute a refund.",
    ),
}

BUSINESS_WRITE_EFFECTS = frozenset(
    {"business_write", "refund", "payment", "account_change", "delete", "charge"}
)

# Tools the pipeline itself may call after the route is final.
SYSTEM_TOOLS: dict[str, tuple[str, ...]] = {
    "auto_reply_faq": ("lookup_faq",),
    "logistics_queue": ("lookup_order_status", "route_to_queue"),
    "billing_queue": ("lookup_order_status", "route_to_queue"),
    "support_queue": ("route_to_queue",),
    "security_review": ("create_ticket_note", "route_to_queue"),
    "human_review": ("create_ticket_note",),
}


class ToolError(PermissionError):
    pass


def invoke(name: str, route: str, allowlist: tuple[str, ...]) -> dict[str, str]:
    """Run a stub tool. Refuses names outside the registry or the allowlist."""
    if name not in REGISTRY:
        raise ToolError(f"unknown tool: {name}")
    if name not in allowlist:
        raise ToolError(f"tool {name} is outside the allowlist for {route}")
    if name == "lookup_faq":
        return {"text": FAQ_REPLY}
    if name == "lookup_order_status":
        return {"status": "in_transit"}
    if name == "create_ticket_note":
        return {"noted": "true"}
    if name == "route_to_queue":
        return {"queue": route}
    raise ToolError(f"unhandled tool: {name}")
