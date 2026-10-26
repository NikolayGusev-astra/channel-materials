"use strict";
// Clean re-implementation of the promo-code validator, reconstructed from
// observed behavior of the compiled bundle (no code copied).

// 32-char alphabet without ambiguous glyphs (no I, O, 0, 1).
const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const MODULUS = 31;

function charIndex(ch) {
  return ALPHABET.indexOf(ch);
}

// Weighted polynomial hash of the first 7 chars -> checksum value 0..30.
function computeChecksum(chars7) {
  let acc = 0;
  for (let i = 0; i < chars7.length; i++) {
    const idx = charIndex(chars7[i]);
    if (idx < 0) return -1;
    acc = (acc * 3 + idx * (i + 1)) % MODULUS;
  }
  return acc;
}

// Discount table lookup derived from a base-31 roll of the 4-char prefix.
const DISCOUNT_TABLE = [10, 10, 15, 10, 20, 15, 10];

function discountForPrefix(prefix4) {
  let acc = 0;
  for (const ch of prefix4) {
    acc = (acc * 31 + charIndex(ch)) >>> 0;
  }
  return DISCOUNT_TABLE[acc % DISCOUNT_TABLE.length];
}

const CODE_RE = /^([A-Z2-9]{4})-([A-Z2-9]{4})$/;

function validate(raw) {
  if (typeof raw !== "string") {
    return { ok: false, reason: "type" };
  }
  const normalized = raw.trim().toUpperCase();
  const match = CODE_RE.exec(normalized);
  if (!match) {
    return { ok: false, reason: "format" };
  }
  const prefix = match[1];
  const body = prefix + match[2];
  const expected = computeChecksum(body.slice(0, 7));
  if (charIndex(body[7]) !== expected) {
    return { ok: false, reason: "checksum" };
  }
  return { ok: true, discount: discountForPrefix(prefix), reason: null };
}

module.exports = { validate };
