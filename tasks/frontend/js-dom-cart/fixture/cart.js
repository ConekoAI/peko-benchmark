// cart.js — cart logic for the demo shop page (ES module, no dependencies).

export function createCart() {
  return { items: [] };
}

export function addItem(cart, { id, name, price, qty = 1 }) {
  const existing = cart.items.find((it) => it.id === id);
  if (existing) {
    existing.qty += qty;
    return cart;
  }
  cart.items.push({ id, name, price, qty });
  return cart;
}

export function removeItem(cart, id) {
  cart.items = cart.items.filter((it) => it.id !== id);
  return cart;
}

export function setQuantity(cart, id, qty) {
  // BUG: qty <= 0 should remove the item; instead a 0/negative-qty line
  // lingers in the cart.
  const item = cart.items.find((it) => it.id === id);
  if (item) item.qty = qty;
  return cart;
}

export function total(cart) {
  // BUG: raw float sum drifts (0.1 * 3 → 0.30000000000000004); money
  // totals must be rounded to cents.
  return cart.items.reduce((sum, it) => sum + it.price * it.qty, 0);
}

export function itemCount(cart) {
  return cart.items.reduce((n, it) => n + it.qty, 0);
}
