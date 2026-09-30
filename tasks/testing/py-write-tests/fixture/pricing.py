"""pricing — discount rules for a small shop. Stdlib only."""

from __future__ import annotations


def unit_price(base: float, discount_pct: float = 0) -> float:
    """Apply a percentage discount to a unit price, rounded to cents.

    Raises ValueError if discount_pct is outside [0, 90].
    """
    if discount_pct < 0 or discount_pct > 90:
        raise ValueError(f"discount_pct out of range: {discount_pct}")
    return round(base * (1 - discount_pct / 100), 2)


def bulk_discount_pct(qty: int) -> int:
    """Bulk tier for a quantity: 10+ → 5%, 50+ → 12%, 200+ → 20%."""
    if qty >= 200:
        return 20
    if qty >= 50:
        return 12
    if qty >= 10:
        return 5
    return 0


def order_total(base: float, qty: int, member: bool = False) -> float:
    """Total for `qty` units of `base` unit price.

    The bulk tier applies first; members then get an extra 3% off the
    discounted total. The result is rounded to cents.
    """
    pct = bulk_discount_pct(qty)
    price = unit_price(base, pct)
    total = price * qty
    if member:
        total = round(total * 0.97, 2)
    return round(total, 2)
