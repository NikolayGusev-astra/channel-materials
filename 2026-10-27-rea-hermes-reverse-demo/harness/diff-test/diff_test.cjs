// Дифференциальный тест: оригинальный бандл против пере-реализации.
// Запуск: node diff_test.js <path-to-rebuild.js> [N]
const path = require("path");
const fs = require("fs");

const N = parseInt(process.argv[3] || "10000", 10);
const rebuildPath = process.argv[2];
if (!rebuildPath || !fs.existsSync(rebuildPath)) {
  console.error("usage: node diff_test.js <rebuild.js> [N]");
  process.exit(2);
}

const original = require(path.join(__dirname, "..", "promo-app", "app.asar.unpacked", "main.js"));
const rebuild = require(path.resolve(rebuildPath));

const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
// Полный ASCII для строк вне формата: валидатор должен одинаково их классифицировать.
const NOISE = "abcdefghijkmnopqrstuvwxyz01IOol- _!@#$%^&*()";

function rnd(n) { return Math.floor(Math.random() * n); }
function randCode() {
  let s = "";
  for (let i = 0; i < 8; i++) {
    s += ALPHABET[rnd(ALPHABET.length)];
    if (i === 3) s += "-";
  }
  return s;
}
function randGarbage() {
  const len = 1 + rnd(12);
  let s = "";
  for (let i = 0; i < len; i++) s += NOISE[rnd(NOISE.length)];
  return Math.random() < 0.5 ? s : s.toUpperCase();
}

let mismatch = 0;
const samples = [];
for (let i = 0; i < N; i++) {
  const code = i % 2 === 0 ? randCode() : randGarbage();
  const a = JSON.stringify(original.validate(code));
  const b = JSON.stringify(rebuild.validate(code));
  if (a !== b) {
    mismatch++;
    if (samples.length < 5) samples.push({ code, original: a, rebuild: b });
  }
}
const codes = [];
for (let i = 0; i < N; i++) codes.push(i % 2 === 0 ? randCode() : randGarbage());
const discounts = {};
for (const c of codes) {
  const r = original.validate(c);
  if (r.ok) discounts[r.discount] = (discounts[r.discount] || 0) + 1;
}

console.log(JSON.stringify({ n: N, mismatch, discounts, samples }, null, 1));
process.exit(mismatch === 0 ? 0 : 1);
