// Hidden grading tests for the cart task. Copied into the workdir by
// grade.sh — the agent never sees this file.
import test from "node:test";
import assert from "node:assert/strict";

import {
  createCart,
  addItem,
  removeItem,
  setQuantity,
  total,
  itemCount,
} from "./cart.js";

const mug = { id: "p2", name: "Mug", price: 12.99 };
const sticker = { id: "p1", name: "Sticker", price: 0.1 };

test("addItem merges same-id lines", () => {
  const cart = createCart();
  addItem(cart, mug);
  addItem(cart, mug);
  assert.equal(cart.items.length, 1);
  assert.equal(cart.items[0].qty, 2);
});

test("setQuantity(0) removes the item", () => {
  const cart = createCart();
  addItem(cart, mug);
  setQuantity(cart, mug.id, 0);
  assert.equal(cart.items.length, 0);
  assert.equal(itemCount(cart), 0);
});

test("setQuantity(negative) removes the item", () => {
  const cart = createCart();
  addItem(cart, mug);
  setQuantity(cart, mug.id, -2);
  assert.equal(cart.items.length, 0);
});

test("total rounds to cents (0.1 * 3)", () => {
  const cart = createCart();
  addItem(cart, sticker, );
  addItem(cart, sticker);
  addItem(cart, sticker);
  assert.equal(total(cart), 0.3);
});

test("total rounds mixed basket", () => {
  const cart = createCart();
  addItem(cart, mug);
  addItem(cart, sticker);
  addItem(cart, { id: "p3", name: "Poster", price: 7.5, qty: 2 });
  assert.equal(total(cart), 28.09);
});

test("total of empty cart is 0", () => {
  assert.equal(total(createCart()), 0);
});

test("removeItem still works", () => {
  const cart = createCart();
  addItem(cart, mug);
  addItem(cart, sticker);
  removeItem(cart, mug.id);
  assert.deepEqual(cart.items.map((it) => it.id), ["p1"]);
});
