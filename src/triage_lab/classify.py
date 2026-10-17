"""Deterministic keyword profiles used by the simulated providers.

``rules_baseline`` is exact phrases after accent folding.
``large_sim`` adds typo folding, quote/signature cuts, negation and extra phrases.
``small_sim`` starts from the keyword rules and then flips a configured fraction
of message ids. Those flips are simulated by construction.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

ACCENTS = str.maketrans(
    {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }
)

TYPOS = {
    "rembolso": "reembolso",
    "chnage": "change",
    "shiping": "shipping",
    "pedio": "pedido",
    "chargd": "charged",
    "dimentions": "dimensions",
    "abogodo": "abogado",
    "demadar": "demandar",
    "clik": "click",
    "cliam": "claim",
}

NEGATIONS = (
    "no quiero",
    "no busco",
    "no pido",
    "not asking",
    "not a refund",
    "i am not asking",
    "todavia no",
    "sin reembolso",
    "no es un reembolso",
)
NEGATED_CATEGORIES = frozenset({"refund_request", "abuse_or_legal"})

PRECEDENCE = (
    "abuse_or_legal",
    "spam",
    "refund_request",
    "payment_issue",
    "shipping_address_change",
    "order_status",
    "complaint",
    "product_question",
)

BASE: dict[str, tuple[str, ...]] = {
    "abuse_or_legal": (
        "abogado",
        "lawyer",
        "demanda",
        "lawsuit",
        "legal action",
        "accion legal",
        "juicio",
    ),
    "spam": (
        "crypto giveaway",
        "cripto gratis",
        "click here to claim",
        "hace clic aqui",
        "premio exclusivo",
    ),
    "refund_request": (
        "reembolso",
        "refund",
        "money back",
        "devolver el dinero",
        "que me devuelvan",
    ),
    "payment_issue": (
        "me cobraron",
        "charged twice",
        "double charge",
        "pago rechazado",
        "card declined",
    ),
    "shipping_address_change": (
        "cambiar la direccion",
        "change the address",
        "cambio de domicilio",
        "direccion de envio",
        "shipping address",
    ),
    "order_status": (
        "donde esta mi pedido",
        "where is my order",
        "where is order",
        "numero de seguimiento",
        "tracking number",
        "estado del pedido",
        "order status",
        "estado de mi pedido",
    ),
    "complaint": (
        "queja",
        "reclamo",
        "pesimo",
        "complaint",
        "muy disconforme",
        "file a complaint",
    ),
    "product_question": (
        "como se lava",
        "washing",
        "medidas",
        "dimensions",
        "de que esta hecho",
        "instrucciones de",
        "material",
    ),
}

EXTRA: dict[str, tuple[str, ...]] = {
    "abuse_or_legal": ("defensa del consumidor", "denunciar", "demandar", "court"),
    "spam": ("crypto prize", "claim your prize"),
    "refund_request": (
        "devolverme lo que pague",
        "return what i paid",
        "money returned",
    ),
    "payment_issue": ("cargo duplicado", "cobro duplicado", "charged me twice"),
    "shipping_address_change": ("otra casa", "mudanza", "new address"),
    "order_status": ("where is my pedido", "seguimiento"),
    "complaint": ("atencion fue mala", "dio bola", "very unhappy"),
    "product_question": ("se puede lavar", "lavar", "how do i wash", "talla"),
}

SMALL_FLIP_MOD = 5
LARGE_FLIP_MOD = 17
CATEGORIES = (
    "order_status",
    "shipping_address_change",
    "refund_request",
    "payment_issue",
    "product_question",
    "complaint",
    "abuse_or_legal",
    "spam",
    "other",
)


@dataclass(frozen=True)
class HeuristicPrediction:
    category: str
    confidence: float
    margin: int
    flipped: bool


def stable_hash(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def fold_accents(text: str) -> str:
    return text.lower().translate(ACCENTS)


def fold_typos(text: str) -> str:
    parts = re.findall(r"[a-z0-9]+|[^a-z0-9]+", text)
    return "".join(TYPOS.get(part, part) for part in parts)


def cut_noise(text: str) -> str:
    """Drop quoted threads and signature blocks from folded text."""
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        if "escribio:" in stripped or "wrote:" in stripped:
            break
        if stripped in {"saludos,", "saludos", "thanks,", "thanks", "gracias,", "--"}:
            break
        if stripped.startswith("--"):
            break
        kept.append(line)
    return "\n".join(kept)


def _lexicon(extra: bool) -> dict[str, tuple[str, ...]]:
    merged: dict[str, tuple[str, ...]] = {}
    for category in PRECEDENCE:
        phrases = BASE[category]
        if extra:
            phrases = phrases + EXTRA[category]
        merged[category] = phrases
    return merged


def _negated(text: str, start: int) -> bool:
    window = text[max(0, start - 60) : start]
    return any(phrase in window for phrase in NEGATIONS)


def _hits(
    text: str, lexicon: dict[str, tuple[str, ...]], *, negation: bool
) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for category, phrases in lexicon.items():
        for phrase in phrases:
            start = text.find(phrase)
            if start < 0:
                continue
            if negation and category in NEGATED_CATEGORIES and _negated(text, start):
                continue
            found.append((category, start))
    return found


def _rules_pick(hits: list[tuple[str, int]]) -> tuple[str, int]:
    if not hits:
        return "other", 0
    present = {category for category, _start in hits}
    for category in PRECEDENCE:
        if category in present:
            margin = sum(1 for item, _start in hits if item == category)
            return category, margin
    return "other", 0


def _earliest_pick(hits: list[tuple[str, int]]) -> tuple[str, int]:
    if not hits:
        return "other", 0

    def sort_key(item: tuple[str, int]) -> tuple[int, int]:
        category, start = item
        rank = PRECEDENCE.index(category) if category in PRECEDENCE else 99
        return (start, rank)

    category = sorted(hits, key=sort_key)[0][0]
    margin = sum(1 for item, _start in hits if item == category)
    return category, margin


def _rules_confidence(margin: int) -> float:
    if margin <= 0:
        return 0.33
    return min(0.93, 0.48 + 0.15 * margin)


def _large_confidence(margin: int, flipped: bool) -> float:
    if flipped:
        return 0.41
    if margin <= 0:
        return 0.36
    return min(0.97, 0.74 + 0.08 * margin)


def _small_confidence(message_id: str) -> float:
    unit = (stable_hash(message_id) % 100) / 100
    return round(0.58 + unit * 0.37, 4)


def _flip(category: str, message_id: str) -> str:
    others = [item for item in CATEGORIES if item != category]
    # Salted so the draw is not the same hash that assigns the dev/test split.
    return others[stable_hash(f"{message_id}:flip-target") % len(others)]


def score_rules(text: str) -> HeuristicPrediction:
    folded = fold_accents(text)
    category, margin = _rules_pick(_hits(folded, _lexicon(False), negation=False))
    return HeuristicPrediction(category, _rules_confidence(margin), margin, False)


def score_large(text: str) -> HeuristicPrediction:
    """Large profile before the configured id flip."""
    folded = cut_noise(fold_typos(fold_accents(text)))
    category, margin = _earliest_pick(_hits(folded, _lexicon(True), negation=True))
    return HeuristicPrediction(
        category, _large_confidence(margin, False), margin, False
    )


def score_profile(name: str, text: str, message_id: str) -> HeuristicPrediction:
    if name == "rules":
        return score_rules(text)
    if name == "large":
        base = score_large(text)
        if stable_hash(f"{message_id}:large") % LARGE_FLIP_MOD == 0:
            return HeuristicPrediction(
                _flip(base.category, message_id),
                _large_confidence(base.margin, True),
                base.margin,
                True,
            )
        return base
    if name == "small":
        base = score_rules(text)
        flipped = stable_hash(f"{message_id}:small") % SMALL_FLIP_MOD == 0
        category = _flip(base.category, message_id) if flipped else base.category
        return HeuristicPrediction(
            category, _small_confidence(message_id), base.margin, flipped
        )
    raise KeyError(name)
