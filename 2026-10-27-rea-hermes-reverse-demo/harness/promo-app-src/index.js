// Промо-валидатор «магазина» — цель реверс-инжиниринга для демо.
// Собирается минифицированным бандлом, исходник восстановителю не показывается.
const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // без I, O, 0, 1
const CHECK_BASE = 31;

function charIndex(c) {
  const i = ALPHABET.indexOf(c);
  return i < 0 ? -1 : i;
}

function checksum(body) {
  let sum = 0;
  for (let i = 0; i < body.length; i++) {
    const v = charIndex(body[i]);
    if (v < 0) return -1;
    sum = (sum * 3 + v * (i + 1)) % CHECK_BASE;
  }
  return sum;
}

function validate(raw) {
  if (typeof raw !== "string") return { ok: false, reason: "type" };
  const code = raw.trim().toUpperCase();
  const m = /^([A-Z2-9]{4})-([A-Z2-9]{4})$/.exec(code);
  if (!m) return { ok: false, reason: "format" };
  const body = m[1] + m[2];
  const expect = checksum(body.slice(0, 7));
  if (charIndex(body[7]) !== expect) return { ok: false, reason: "checksum" };
  return { ok: true, discount: discountFor(m[1]), reason: null };
}

function discountFor(prefix) {
  let h = 0;
  for (let i = 0; i < prefix.length; i++) h = (h * 31 + charIndex(prefix[i])) >>> 0;
  const tiers = [10, 10, 15, 10, 20, 15, 10];
  return tiers[h % tiers.length];
}

module.exports = { validate };
