---
name: session-audit
description: "Audit Hermes session history - attribution, friction, cron health."
---

> Публикационная копия: санитизирована для статьи «Топ-10 скиллов Hermes
> Agent на каждый день» (2026-10-21). Личные пути, внутренние проекты и
> приватные секции удалены; полная версия живёт в Hermes-профиле автора.

# Session Audit & Attribution

## When to Use

- The user asks to review/analyze past Hermes sessions, or "what should I build/fix next".
- Sessions need attributing to projects (keyword matching, below).
- You need evidence for a proposal: pain clusters, nudge counts, tool error rates, cron
  incident counts. Report counts and let them rank the work — never impressions.

## Context

Hermes Agent stores sessions in `state.db` (table `sessions`) and projects in `projects.db` (table `projects`). There is NO direct foreign key between sessions and projects. Attribution must be done by keyword matching in session metadata.

## Key Facts

- **state.db** path: `%HERMES_HOME%/state.db` (Windows: `%LOCALAPPDATA%\hermes\state.db`)
- **projects.db** path: `%HERMES_HOME%/projects.db` (рядом со state.db)
- На машине может лежать несколько копий `state.db`; живая — та, что под `HERMES_HOME`.
  Перед аудитом проверь размер и дату: устаревшая копия даёт тихо неверные цифры.
- Sessions table columns: `id, source, title, cwd, git_repo_root, chat_type, chat_id, message_count, started_at, last_activity_description, parent_session_id, archived, hidden, end_reason, display_name, session_key, origin_json`
- `sessions.started_at` is a UNIX float timestamp, not ISO. `sessions.last_activity_at` exists; there
  is NO `last_active` column.
- `messages` table FK column is `session_id`; its time column is **`timestamp`**, NOT `created_at`.
  Requesting `m.created_at` fails with `no such column`.
- `messages.tool_name` (role='tool') is the authoritative source of which tools actually ran;
  `sessions.tool_names` is the *available* toolset, not usage — do not count it as usage.
- Projects table columns: `id, slug, name, description, icon, color, board_slug, primary_path, created_at, archived`
- `parent_session_id` links continuation sessions to their parent
- `end_reason` can be `startup_orphan_reap` or `ws_orphan_reap` (system artifacts, not real sessions)

## Attribution Rules

### Keyword → Project mapping (строится под своё окружение)

Прямого внешнего ключа нет, поэтому сессии разносятся по проектам ключевыми
словами из title/cwd/git_repo_root. Правила:

- каждому проекту — свой набор якорных слов (название репо, каталога, продукта);
- порядок проверки фиксирован: специфичные якоря раньше общих
  (проектный стенд раньше продукта, продукт раньше «всего остального»);
- конфликт решает приоритет, а не порядок строк в базе.

### Continuation sessions

Sessions with `parent_session_id` inherit attribution from their parent. Do NOT attribute them independently.

### Exclude

Sessions with `end_reason IN ('startup_orphan_reap', 'ws_orphan_reap')` are system artifacts. Exclude from attribution.

## Implementation

1. Создать недостающие проекты в `projects.db` с корректным `primary_path`.
2. Закрыть/заархивировать проекты-однодневки (`archived=1`).
3. Разнести сессии по проектам (колонка `project_id` или таблица маппинга).
4. Проверить сводным запросом: все не-cron сессии атрибутированы.

## Reading the DB (read-only, Windows)

Open read-only so a live gateway cannot be disturbed and no lock is taken:

```python
con = sqlite3.connect('file:' + os.environ['HERMES_HOME'].replace('\\','/') + '/state.db?mode=ro', uri=True)
```

Use the native `C:/...` forward-slash path. MSYS `/c/Users/...` paths fail from native Python
with `unable to open database file` (MSYS path translation is disabled for native programs).

## Recovering one session by id

When the user references a past session by id (a session this one "continues"), reconstruct its
full picture before working: `runtime/active_sessions.json` + `desktop/interrupted_turns.json` +
state.db extracts (compaction summary first, then user messages, then last assistant turns).
Full recipe and verified column names: `references/session-recovery-recipe.md`.

## Skill usage frequency (which skills actually run)

"What skills are most used" is answered from `messages.tool_calls` (role='assistant',
`tool_calls IS NOT NULL`), never from `sessions.tool_names` (available toolset, not usage).
Each row's `tool_calls` is JSON: a list of calls, or a dict with a `calls` key; each call
holds the name either top-level or under `function`, and arguments as a JSON string or dict.
Parse defensively and count `skill_view` calls by `arguments.name`:

```python
import sqlite3, json, collections
con = sqlite3.connect('file:' + os.environ['HERMES_HOME'].replace('\\','/') + '/state.db?mode=ro', uri=True)
counter = collections.Counter()
for (tc,) in con.execute("SELECT tool_calls FROM messages WHERE role='assistant' AND tool_calls IS NOT NULL"):
    try: calls = json.loads(tc)
    except Exception: continue
    if isinstance(calls, dict): calls = calls.get('calls', [calls])
    for c in calls if isinstance(calls, list) else []:
        if not isinstance(c, dict): continue
        args = c.get('arguments') or c.get('function', {}).get('arguments') or ''
        if isinstance(args, str):
            try: args = json.loads(args)
            except Exception: continue
        if (c.get('name') or c.get('function', {}).get('name')) == 'skill_view' and isinstance(args, dict):
            counter[args.get('name', '?')] += 1
```

Report top-N with counts and state the scan base (rows scanned, total calls, distinct skills).
A full scan of ~192k tool-call rows takes ~12 s in one pass; do it in Python, not per-row queries.
`SELECT DISTINCT tool_name FROM messages WHERE role='tool'` is a quick first look at which
tools ever ran, but frequency needs the assistant-side `tool_calls` parse above.

## Friction audit (what hurts, ranked by count)

The DB answers "what should we build/fix" with numbers, not impressions. Recipe and full queries:
`references/friction-audit-queries.md`. Four signals, computed on `source IN ('desktop','telegram','cli')`
(separate cron from real user work):

1. **Nudge messages** — user messages shorter than ~15 chars (`дальше`, `продолжай`, `статус?`,
   `готово?`). A high count means long tasks run with no progress visibility; the fix is a
   progress/status surface, not more agent effort.
2. **Tool error rate** — grep tool results for `Traceback|error:|No such file|timed out|refused|unable to`.
   Report errored/total per tool. A tool at >40% is a workflow defect worth a dedicated fix.
3. **First-message clustering** — take the first user message per session, keyword-bucket it into
   domains. Gives the task mix. A session can land in several buckets; count separately.
4. **Cron health** — see below.

Report findings as a table of counts with the evidence query behind each number. Never assert
"the user struggles with X" without a count.

## Model-defect attribution (which model produces garbage)

When output defects appear (leaked tool-call markup, malformed turns), attribute them to the
model with counts, not impressions:

- Join `messages` to `session_model_usage(session_id, model, ...)` to get the model behind
  each session.
- A tool-call leak lands in `messages.content` (markup in the text) with `tool_calls` NULL and
  `finish_reason='stop'`; native calls populate the `tool_calls` column. That split is the proof
  the model bypassed the function-calling channel and printed its call syntax as text.
- Report a RATE (malformed / total assistant messages per model), never the raw hit count: a
  ~1% glitch class calls for a strip-guard in the harness, constant breakage calls for pulling
  the model from routing — opposite fixes, and the rate is what chooses between them. The user
  keeps an otherwise-good model that glitches rarely; fix the receiving side.
- Request dumps (`HERMES_HOME/sessions/request_dump_*.json`) hold the outgoing request and the
  transport error only; response-side leakage never appears in them. Grep `messages.content`.

## Cron health (the blind spot)

Three sources, all under `HERMES_HOME/cron/`:

- `jobs.json` — `data['jobs']` list; each job has `id, name, schedule{display}, enabled, last_status`.
- `executions.db` — tables `executions` and `cron_incidents`.
  `cron_incidents` columns: `job_id, error_sig, state (detected|alerted|resolved|closed), failure_type, error, first_seen_at, last_seen_at`.
  `failure_type` buckets: `auth, agent, config, rate_limit, script, timeout, unknown`.
- `usage_audit.jsonl` — per-run usage.

Open-incident count = incidents with `state NOT IN ('closed','resolved')`. Group the `error`
text by `failure_type` and by recurring prefix (a too-small context window and an unloadable
model show up as `config`/`agent` respectively). Job `last_status` alone is stale — cross-check
against `executions.db` incidents before reporting.

## Turning findings into a build proposal

An audit usually ends in "what should I build". Before proposing to write a plugin or tool,
check coverage first — a standing user correction: *«сначала посмотри что из официальных
плагинов hermes agent закроет боли»*.

Check, in order: the curated catalog (`hermes plugins browse`, `hermes plugins search --json`;
~550 entries, tiers official / community), the bundled-but-disabled plugins, and core CLI
commands (`hermes cron doctor`, `hermes cron incidents`, `hermes plugins doctor`). Deliver a
coverage table (pain → existing plugin / built-in / core command) and propose new code only
for the hole that remains. Command set, tier/platform caveats and the docs page map:
skill `hermes-desktop-plugin`, section "Before building".

## Verification

After attribution, run:
sql
SELECT p.slug, p.name, COUNT(s.id) as session_count
FROM projects p
LEFT JOIN sessions s ON s.project_id = p.id
WHERE p.archived = 0
GROUP BY p.id, p.slug, p.name
ORDER BY session_count DESC;

All non-cron sessions should be attributed (except orphan_reap artifacts). No session should be left unattributed.
