"""MUTANT: member discount silently dropped from order_total."""

from __future__ import annotations


def unit_price(base: float, discount_pct: float = 0) -> float:
    if discount_pct < 0 or discount_pct > 90:
        raise ValueError(f"discount_pct out of range: {discount_pct}")
    return round(base * (1 - discount_pct / 100), 2)


def bulk_discount_pct(qty: int) -> int:
    if qty >= 200:
        return 20
    if qty >= 50:
        return 12
    if qty >= 10:
        return 5
    return 0


def order_total(base: float, qty: int, member: bool = False) -> float:
    pct = bulk_discount_pct(qty)
    price = unit_price(base, pct)
    total = price * qty
    # MUTATION: member branch removed — members pay full post-bulk price.
    return round(total, 2)
