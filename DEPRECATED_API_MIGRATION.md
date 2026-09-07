# Deprecated API Usage Audit — `channel-materials`

Date: 2026-09-08  
Scope: `C:\Work\Assist\channel-materials`  
Status: Findings only. No source files modified.

---

## Summary

| Severity | Count | Notes |
|---|---|---|
| High | 1 | Hardcoded legacy Telegram Bot API method without compatibility guard |
| Medium | 1 | Python 2-era constructs in modern script |
| Low | 3 | Stale/curl-based external API references in skill docs/scripts |

---

## Detailed Findings

### 1. HIGH — Hardcoded Telegram `sendMessage` Bot API method
- **File:** `2026-09-07-bonus4\text\send_tg.py`
- **Line:** 14
- **Deprecated / at-risk symbol:** `https://api.telegram.org/bot{token}/sendMessage`
- **Why it matters:** Direct HTTP calls to Bot API bypass official clients, skip automatic retries/backoff, and tightly couple to a single method. Telegram has evolved Bot API semantics around media groups, inline keyboards, and HTTP error behavior.
- **Suggested replacement:** Use `python-telegram-bot` v20+ (`Application.builder().token(...).build()` + `await application.bot.send_message(...)`) or `requests` with structured error handling. Move token to env/config; never inline-read `.env` in a script.
- **Estimated effort:** ~1–2 hours.

---

### 2. MEDIUM — Python 2-style constructs in downloader
- **File:** `2026-09-07-bonus4\download-bonus4-bundle.py`
- **Lines:** 66–93
- **Deprecated / at-risk pattern:** Manual `urllib.request` resume via `Range` header + raw `r.read(chunk)` loop.
- **Why it matters:** Fragile for large files, no retry/backoff, no timeout hygiene beyond `urlopen(timeout=...)`, and no HTTPS cert verification controls. Modern tooling handles resumable downloads and progress natively.
- **Suggested replacement:** `httpx` or `requests` with `Range` + exponential backoff + tqdm, or invoke `aria2c`/`curl` via subprocess when available. Keep resume semantics, but delegate edge cases.
- **Estimated effort:** ~1–2 hours.

---

### 3. LOW — Curl-based live API references in skill docs/scripts
- **Files:**
  - `2026-09-07-model-routing\skill\SKILL.md` (lines 359, 361, 363, 368)
  - `2026-09-07-model-routing\skill\SKILL-PROTOCOL.md` (lines 44, 59)
  - `2026-09-07-model-routing\skill\scripts\route.py` (lines 50, 55)
- **Deprecated / at-risk symbols:** Raw `curl` examples hitting:
  - `openrouter.ai/api/v1/models`
  - `openrouter.ai/api/v1/chat/completions`
  - `kilo.ai/api/models`
  - `hermes-agent.nousresearch.com/docs/api/model-catalog.json`
- **Why it matters:** These are *protocol docs*, not runtime code, but they ship hardcoded provider/model strings (`tencent/hy3:free`, `gpt-5.6-terra`, `gpt-5.6-sol`, `glm-5.3`). Free-model pools rotate fast; stale examples become broken instructions.
- **Suggested replacement:** Replace raw curl snippets with `python` snippets using `httpx` (or `requests`) + JSON parsing, and add a clear note: “Verify current free model IDs before use; they rotate weekly.”
- **Estimated effort:** ~30–60 minutes per doc file.

---

## Migration Plan (ordered by risk/impact)

1. **P0 — `send_tg.py` Telegram Bot API call**
   - Risk: Token + single-method HTTP coupling; breakage is silent until runtime.
   - Action: Switch to `python-telegram-bot` v20+ or structured `requests` wrapper; externalize token; add retry/timeout.

2. **P1 — `download-bonus4-bundle.py` downloader**
   - Risk: Large-file corruption / stall without backoff; resume logic is brittle.
   - Action: Replace manual `urllib` loop with `httpx` stream + retry + progress, or delegate to system `curl`/`aria2c`.

3. **P2 — `SKILL.md` / `SKILL-PROTOCOL.md` curl snippets**
   - Risk: Documentation drift; broken instructions when provider endpoints/models rotate.
   - Action: Convert to versioned `httpx` snippets; add “refresh cadence” note; snapshot current free model IDs in `lm-studio-test/raw/` as a reference baseline.

4. **P3 — `route.py` provider strings**
   - Risk: Same as P2, but embedded in code path strings.
   - Action: Externalize provider/model catalog to a JSON/YAML file loaded at runtime, with a script to refresh it from live endpoints.

---

## Files Reviewed

- `2026-09-07-bonus4\text\send_tg.py`
- `2026-09-07-bonus4\download-bonus4-bundle.py`
- `2026-09-07-model-routing\skill\scripts\route.py`
- `2026-09-07-model-routing\skill\SKILL.md`
- `2026-09-07-model-routing\skill\SKILL-PROTOCOL.md`
