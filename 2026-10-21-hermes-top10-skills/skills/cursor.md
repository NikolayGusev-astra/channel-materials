---
name: cursor
description: >-
  Диспетчер группы портированных Cursor-скиллов и инженерных портов (78 Cursor
  + 25 addyosmani/agent-skills). По запросу сам определяет (через LLM), какие из
  портированных скиллов применимы, подгружает нужный через skill_view и применяет.
  При неоднозначности — уточняет через clarify. Вызов: /cursor <задача>.
---

> Публикационная копия: санитизирована для статьи «Топ-10 скиллов Hermes
> Agent на каждый день» (2026-10-21). Личные пути, внутренние проекты и
> приватные секции удалены; полная версия живёт в Hermes-профиле автора.

# cursor — диспетчер портированных Cursor-скиллов

Группа из 78 портированных Cursor-скиллов (`github.com/cursor/plugins`, snapshotted
2026-07-16) + 25 инженерных портов `addyosmani/agent-skills` (snapshotted 2026-09-07,
префикс `agent-skills-`). Этот скилл — **роутер**: понимает запрос на естественном языке и сам
решает, что применить. Не каталог для ручного листания (хотя индекс тоже лежит рядом).

## Обязательное правило: явный вызов `/cursor` значит выполнять, а не обсуждать

Когда пользователь явно пишет `/cursor ...` или «используй /cursor», это директива
запустить соответствующие портированные скиллы в этом же сеансе. После выбора
скиллов сразу применяй их через `skill_view(...)` и соответствующие действия
Hermes (`terminal`, `patch`, `delegate_task` и т.д.). Не ограничивайся подтверждением
или планом — `/cursor` уже означает «делай».

`/cursor` здесь — диспетчер скиллов, а не требование установленного Cursor CLI.
Сначала загрузи этот скилл и выбранные порты; наличие `cursor`, `agent` или
`cursor-agent` в PATH не является gate для применения workflow. Отдельно
выполняй запрос на frontier-модель: загрузи `dev/model-routing`, выбери модель
явно и сообщай фактически использованный исполнитель/модель, не приписывая
обычной делегации frontier-статус без подтверждения.

Для аудита плагинов и вложенных модулей используй
`references/plugin-audit.md`: проверка checkout/deploy/submodule и поведенческие
пробы до рекомендаций по упрощению или удалению.

## Алгоритм работы

Когда пользователь вызывает `/cursor <что-то>`:

### 1. Загрузи индекс скиллов
Прочитай файл `~/AppData/Local/hermes/skills/_cursor_index.md` (рядом с этим скиллом,
в `skills/`). Там — таблица всех 78 скиллов, сгруппированная по плагинам, с назначением
каждого. Это твоя база для маршрутизации.

### 2. Определи применимые скиллы (LLM-роутинг)
По смыслу запроса выбери **один или несколько** подходящих скиллов из индекса.
Примеры сопоставления смысл → скилл:
- «сделай code review / проверь качество кода» →
  `thermos-thermo-nuclear-code-quality-review`, `cursor-team-kit-review-and-ship`,
  `pstack-interrogate`
- «почини CI / тесты падают в пайплайне» →
  `cursor-team-kit-fix-ci`, `cursor-team-kit-loop-on-ci`,
  `cursor-team-kit-run-smoke-tests`
- «напиши код через TDD / red-green-refactor» → `pstack-tdd`
- «запусти параллельных агентов / распараллель задачу» → `orchestrate-orchestrate`
- «убери AI-слап из кода / почисти стиль» → `cursor-team-kit-deslop`,
  `pstack-unslop`, `pstack-show-me-your-work`
- «сделай PR удобным для ревью» → `cursor-team-kit-make-pr-easy-to-review`
- «создай новый плагин / скилл» → `create-plugin-create-plugin-scaffold`,
  `pstack-poteto-mode` (playbook authoring-a-skill)
- «заспавнь итеративный цикл / самореф-луп» → `ralph-loop-ralph-loop`
- «спроектируй agent-loop / review-gated цикл / LLM-as-judge / multi-model
  council / построй self-review цикл / looper» → `looper-looper`
- «спроектируй API / контракт модуля / REST-эндпоинт» → `agent-skills-api-and-interface-design`
- «закрой уязвимости / hardening / аудит зависимостей» → `agent-skills-security-and-hardening`
- «добавь логирование/метрики/трейсинг/алерты» → `agent-skills-observability-and-instrumentation`
- «оптимизируй перформанс / N+1 / Core Web Vitals» → `agent-skills-performance-optimization`
- «подготовь деплой / staged rollout / rollback-план» → `agent-skills-shipping-and-launch`
- «настрой CI/CD / quality gates в пайплайне» → `agent-skills-ci-cd-and-automation`
- «какой моделью делать / выбери модель / экономь лимиты / usage limit что
  делать / хочу локального оркестратора» → `dev/model-routing` (скоринг
  сложности → категория → цепочка провайдеров из 3 звеньев; перед
  каждым codex/zcode-делегатом; **валидированный локальный оркестратор
  `google/gemma-4-e4b` + fallback `hermes-route` CLI**)
- «проверь совместимость репо с агентами» → `agent-compatibility-check-agent-compatibility`
- «спроектируй CLI для агента» → `cli-for-agent-cli-for-agents`
- «делегируй задачу в ZCode / Zhipu / Z.AI coding agent» →
  `zcode-delegation` (скилл группы autonomous-ai-agents: headless `zcode.cjs`
  `-p`, coding-plan подписка, anthropic-эндпоинт)
- «визуализируй PR / документацию» → `pr-review-canvas-pr-review-canvas`,
  `docs-canvas-docs-canvas`
- «строй на Cursor SDK» → `cursor-sdk-cursor-sdk`
- «обнови память агента по сессии» → `continual-learning-continual-learning`
- «обучи / составь план обучения» → `teaching-create-learning-path`,
  `teaching-run-learning-retrospective`
- «DeepSeek Harness / dsh / агентный фреймворк DeepSeek / всё-плагин /
  cordis.yml-композиция / dsh web / dsh plugin» → `deepseek-harness`
  (нативный knowledge-base скилл, НЕ из 78 портов: запуск, конфигурация
  провайдеров, разработка плагинов, Python SDK; подгружай его references/
  через `skill_view` по мере надобности — см. раздел «deepseek-harness» ниже)

Если запрос многосложный — выбери **несколько** скиллов и примени их по порядку
(например: TDD → deslop → review-and-ship).

### 3. Реши: хватает ли контекста
- **Уверен и однозначно** → переходи к шагу 4.
- **Неоднозначно** (несколько кандидатов, или непонятно, что именно нужно пользователю)
  → вызови `clarify` с 2–4 вариантами из отобранных скиллов + кратким пояснением
  каждого. НЕ гадай молча. После ответа пользователя — шаг 4.
- **Ничего не подходит** из 78 → скажи честно, что в группе cursor такого нет,
  и предложи ближайший по смыслу либо нативный подход Hermes.

### 4. Подгрузи и примени выбранный скилл
Для каждого выбранного скилла:
1. `skill_view(name='<skill-name>')` — загрузи его содержимое.
2. Если в нём есть linked_files (references/, scripts/, playbooks/ и т.п.) —
   при необходимости догрузи через `skill_view(name='<skill-name>', file_path='...')`.
3. Примени инструкции скилла, **адаптируя под Hermes** (см. ниже).

### 5. Адаптация под Hermes (обязательно)
Каждый портированный скилл содержит блок «Адаптация под Hermes». Ключевые правила:
- Cursor subagents (`agents/*.md`, `prompts/*.md`) → `delegate_task` с текстом агента в `context`/`goal` (role: leaf).
- «Run the CLI / check the diff» → `terminal` (git, скрипты), `search_files`, `patch`, `browser`.
- Cursor hooks (`hooks/*.ts`) и slash-команды (`Cmd+Shift+P`, `/foo`) → НЕ запускаются;
  заменяй на `cronjob`, `terminal(background=true)` или native-действия Hermes.
- Скрипты `*.ts`/`*.mjs` в скиллах — реальный код, но обычно достаточно переложить
  логику на shell/python через `terminal` или `execute_code`.

## Пример диалога

> User: `/cursor почини падающий CI и сделай ревью перед мержем`
>
> (роутер грузит индекс, находит cursor-team-kit-fix-ci + cursor-team-kit-loop-on-ci
>  + thermos-thermo-nuclear-code-quality-review, грузит их через skill_view,
>  последовательно применяет через terminal/delegate_task)

> User: `/cursor помоги с агентами`
>
> (неоднозначно → clarify: «Что именно? 1) распараллелить задачу (orchestrate)
>  2) проверить совместимость репо (agent-compatibility) 3) обновить память по сессии
>  (continual-learning)»)

## Заметка
Индекс `_cursor_index.md` генерируется скриптом `scripts/build_cursor_index.py`
(лежит в `skills/cursor/scripts/`, не в `~`). Если добавишь новые портированные
скиллы — перегенерируй. Портированные скиллы живут в
`~/AppData/Local/hermes/skills/<plugin>-<skill>/`, каждый со своим блоком адаптации.
Техника портирования — в `references/porting-recipe.md`.
Пере-порт всех скиллов из `references/` — скриптом `scripts/port_cursor_skills.py`.

## Нативные (не-портированные) скиллы в роутинге
Помимо 78 портов из `_cursor_index.md`, `/cursor` роутит и на несколько нативных
Hermes-скиллов, когда задача про сам инструмент, а не про чужой воркфлоу:

- **`deepseek-harness`** (категория `ai`) — DeepSeek Harness / `dsh`: наш основной
  LLM-стек. Любой запрос «dsh», «DeepSeek Harness», агентный фреймворк DeepSeek,
  cordis.yml-композиция, `dsh web`/`dsh plugin`/`dsh --profile headless` — грузи
  этот скилл через `skill_view` и его references/ по мере надобности:
  - `ai/deepseek-harness/../ai/deepseek-harness/references/architecture.md` — «всё — плагин», профили/бандлы/слои, события,
    turn-flow, сессионный лог, capability-швы, карта точек расширения.
  - `ai/deepseek-harness/../ai/deepseek-harness/references/run-and-cli.md` — запуск (npm/исходники), CLI-режимы, layering.
  - `ai/deepseek-harness/../ai/deepseek-harness/references/plugin-development.md` — минимальный плагин, `inject`,
    `ctx.effect()`, `cordis.yml --patch` (пути — абсолютные).
  - `ai/deepseek-harness/../ai/deepseek-harness/references/providers-and-webui.md` — провайдеры, `$DSH_HOME/settings.yaml`
    (модальности `input`/`defaultInput`), `$DSH_HOME/.credentials.yaml`.
  - `ai/deepseek-harness/../ai/deepseek-harness/references/python-sdk.md` — Python SDK (не Windows: нужен POSIX PTY).
  - `ai/deepseek-harness/../ai/deepseek-harness/references/repo-development.md` — layout репо, `pnpm run *`, tsconfig-агрегаты.

Ключевая практика на этой машине: Windows отсекает Python SDK-агента с
персистентным Bash (нужен POSIX PTY-подложка) — используй Web UI
(`npx @deepseek-ai/dsh web`, порт 3080) или headless; провайдер за PII-шлюзом
цепляется через `DEEPSEEK_BASE_URL` + OpenAI-совместимый endpoint (`GET /models`).

## Параллельный прогон (важно при аудите больших репо)
Когда применяешь несколько read-only скиллов (аудит/понимание) к одному репо —
пускай их параллельно через `delegate_task` (role: leaf), чтобы не жрать контекст
основной сессии. **Лимит параллельных subagents = 3** (`max_concurrent_children`);
дроби пачки по 3 (напр. 8 аудитов = 3+3+2). Их результаты возвращаются сообщениями —
не жди синхронно, продолжай независимую работу (чистка/доки), а правки кода делай
ПОСЛЕ получения аудитов.

## Локальная работа / пуш-гейт
Репо клонируй локально (напр. `projects/<repo>/`) и работай в локальной копии.
**Никогда не пушь и не мержь в main автономно** — только по явному «ок» пользователя.
До того — все правки/коммиты только в локальный git, без push.
Стадируй правки в отдельную ветку (`fix/...`), main не трогай.
Конкретный git-ритуал на каждый TDD-фикс (ветка→commit→ff-merge→push по ок):
см. `references/round-fix-workflow.md`.

## Критично: порядок правок относительно аудита (поймалось на практике)
Если гонишь сквозной воркфлоу аудит → правки → тесты → PR поверх одного репо:
- **НЕ правь код, пока read-only subagents (Фазы аудита/понимания) ещё крутятся.**
  Они читают те же файлы, что собираешься править; твоя правка **исказит их базу**
  и даст рассинхронные/ложные findings. Жди завершения ВСЕХ агентов, своди отчёты,
  и только потом применяй Фазы чистки/фиксов. Это жёсткое правило, не нарушать.
- Между запуском аудитов и их завершением делай только **независимую** работу
  (генерация docs-canvas, анализ CLI, черновики тестов вне `tests/`), которая не
  трогает файлы под аудитом.

## Watchdog на фоновые subagents (пользователь требует каждые 5 мин)
Пока висят read-only агенты — ставь `cronjob` (every 5m), который проверяет, живы ли
они, а не умерли молча. Конкретная проверка: `ls cache/delegation/*.txt`, считать
файлы; ожидаемое число = числу запущенных агентов. Рецепт и важное ограничение
(cron НЕ будит чат в GUI/TUI-сессии — алерты падают в лог крона, поэтому сам
проверяй статус в своих тёрнах) — в `references/watchdog-cronjob.md`.

### Получение результатов async delegation

Используй способ доставки, указанный в ответе `delegate_task`. Если результаты
возвращаются отдельными сообщениями между тёрнами, выполняй только независимую
read-only работу, затем закончи тёрн коротким статусом. Не опрашивай transcript
или кеш в ожидании завершения: это не ускоряет доставку и расходует контекст.
Не объявляй предварительные findings полным аудитом; сведи и перепроверь
результаты после их доставки.

## Тесты / pytest на чужом venv
`python -m pytest` может не найти pytest, если `python` и `pip` смотрят в разные venv
(типично: `python` → venv Hermes без pytest, `pip` → системный с pytest). Фикс:
`python -m pip install pytest pytest-asyncio` (в тот же интерпретатор). Локальный импорт модуля проекта часто работает без полной установки зависимостей (graceful degrade) — проверяй `python -c "import <модуль>"`.
**TDD-честность:** новый тест должен падать (RED) на баг ДО правки. Если поправил код
до теста — временно верни баг (git stash/revert), подтверди RED, верни фикс, подтверди
GREEN. Не выдавай GREEN за доказательство без RED-шага.

## search_files квирк (MSYS)
`search_files` с `target=files` и glob-паттерном (`*.py`) возвращает 0 на MSYS-путях
(`/c/Users/...`). Обходи через `terminal` + `ls`/`grep -r`. Не путай с поломкой
инструмента.

## Live-runtime verification (after code fixes)

When a user asks whether a fixed RAG/memory system **already works**, do not infer this from pytest alone. Route to the relevant `/cursor` workflow (normally `cursor-team-kit-control-cli` + `cursor-team-kit-review-and-ship`) and run a separate readiness pass:

1. Separate **code correctness** (unit suite) from **live readiness** (the service accepts, persists, and retrieves real data).
2. Verify the intended CLI starts and exposes its commands.
3. Inspect feature-gating env/config; for optional backends, confirm that the enable flag and mode are actually set, not merely defaulting to noop.
4. Verify persistent state artifacts are present and usable (если бэкенд хранит состояние: файл капсулы существует и `stats` отвечает).
5. Probe external dependencies at application-protocol level, not merely an open TCP port (для локального инференс-сервера: стабильный `/v1/models` или ответ эмбеддинга).
6. Execute one non-destructive end-to-end probe: record a disposable episode, recall/search it, and clean up only through a supported safe operation.
7. State a precise verdict: **code green**, **runtime ready**, or **runtime blocked**, with exact unmet prerequisites. Never call a service working when only tests are green.

Store deployment-specific paths and incidents in a `references/` file next to the skill, not in the class-level skill itself.

## Windows Codex sandbox pitfall

On Windows, Codex CLI default `workspace-write` sandbox frequently fails with:
`CreateProcessWithLogonW failed: 267`. When this happens, rerun with:
`codex exec --sandbox danger-full-access ...`. Use process boundaries as the
safety layer instead: explicit `workdir`, clean git status before launch, narrow
task prompts, `git diff` review, targeted tests, and confirmation before broad
changes. See `references/windows-codex-sandbox.md`.

## Parallel audit+runtime verification pattern

For production-readiness checks, dispatch two leaf subagents in parallel:
1. Static audit: security, correctness, maintainability, test coverage
2. Live runtime probe: CLI startup, env gating, capsule/state artifacts,
   external dependency protocol check, non-destructive end-to-end probe

Both report back independently. Merge their findings into a single GO/NO-GO
verdict. This avoids sequential waiting and gives both code-level and runtime
evidence before declaring ready.

## Codex prompt sizing rule on Windows

Do not pass a giant monolithic remediation prompt to Codex CLI in one call.
On Windows it often fails with prompt-read/arg-parsing errors.
Use a sequence of narrow, ordered patches instead:
- one defect class per patch,
- explicit file/line targets,
- acceptance test per patch,
- `py_compile` after each patch,
- full `pytest` after each stage.

Когда правишь баг в модуле и пишешь тест через `pstack-tdd`/`thermos-*`:
- **Модульная функция ≠ метод класса.** Если код зовёт `_get_embedding(query)`
  (без self) — это модульная функция. Мокать через
  `mock.patch("unified_searcher._get_embedding", return_value=...)`,
  НЕ `mock.patch.object(UnifiedSearcher, "_get_embedding")` — упадёт
  `AttributeError: class has no attribute` (атрибут ищется на классе, а функция в module globals).
- **aiohttp `session.post()` возвращает НЕ корутину, а context-manager.**
  `async with session.post(...) as resp:` работает, потому что `post()` возвращает
  `_RequestContextManager` (имеет `__aenter__`/`__aexit__`). В тесте мокай
  `MagicMock(return_value=fake_resp)`, где `fake_resp` имеет `async def __aenter__`,
  НЕ `AsyncMock` (он сделает `post()` → корутину, и `async with <coroutine>`
  упадёт с "coroutine never awaited"). Для `resp.headers` используй `@property`,
  не метод.
- **RED перед GREEN обязателен**, но НЕ порть живой код ради ритуала:
  если фикс уже применён и тест GREEN — не откатывай баг в прод просто чтобы
  увидеть RED. Проверяй RED логически (читаешь код до правки) или временным
  stash локально, не коммить откат.
- **Контракт `_get_embedding` при сбое:** возвращает нулевой вектор `[0.0]*DIM`
  (НЕ `None`, НЕ `[]`). Проверка `sum(abs(v))==0` в caller'е = детект сбоя
  embedding-сервиса. Не меняй этот контракт без проверки всех потребителей
  (`grep "_get_embedding\b"` — их может быть 5+ в кодовой базе).

## Явная директива пользователя: «используй /cursor»
Когда пользователь пишет «используй /cursor» (mid-turn out-of-band) — это значит:
каждый последующий фикс/аудит-шаг ФОРМУЛИРУЙ и ПРИМЕНЯЙ через вызов
соответствующего портированного скилла (tdd для правок, deslop/unslop для чистки,
docs-canvas для обзоров), а не ad-hoc режимом. Диспетчер `cursor` остаётся
точкой входа — не переходи на прямые правки без роутинга, если явно сказано /cursor.

### План и исполнение
Если пользователь просит «покажи полный план работ и выполняй»:
1. Сначала составь конечный план только из реально применимых и доступных портированных скиллов. Не обещай скилл, пока не подтвердил его наличие через `skill_view` или список доступных скиллов.
2. Для каждого пункта укажи проблему, выбранный skill, границу изменения, способ проверки и push-гейт.
3. Исполняй последовательно: read-only проверка → минимальная правка → targeted test → полный suite → отдельный коммит/пуш только при явном разрешении.
4. Если аудитная находка не подтверждается в текущем коде, пометь её «не баг» и не делай фиктивную правку. Если модуль используется в production/eval-пути, не удаляй его лишь по пометке deprecated.
5. Для больших дубликатов сначала сравни контракт и платформенный конфиг. Выноси только идентичные чистые хелперы; различающуюся платформенную логику оставляй локальной.
6. В финале явно раздели: выполнено и проверено; сознательно отложено как архитектурный рефактор; проверено и признано не багом.

**Plan → Codex handoff (greenfield / migration plans):** когда план написан через `writing-plans` (многофазный, TDD-субтаски, см. его раздел «Multi-Phase Plans & Cross-Task Consistency»), исполняй через Codex узкими промптами — один промпт на 1-2 Task ("Execute docs/plans/phaseX.md Task N.N"). Каждый Task: RED→GREEN→commit локально. **НЕ пушь без явного «ок» пользователя** (standing push-gate выше). Перед началом следующей фазы гоняй `python -m pytest tests -q` и сверяй с baseline. Обязательно прогони само-ревью чеклист из `writing-plans` ДО сохранения плана — он ловит test/impl interface drift, неявные cross-phase зависимости и mismatch в тестовых данных, которые иначе всплывут только при исполнении Codex.

**Codex handoff: ВСЕГДА задавай модель явно (`-m`).** Иначе делегация/субагент скатывается к устаревшему `gpt-4o`. Доступные на ChatGPT-аккаунте: `gpt-5.6-luna` (fast/cheap — дефолт рутины), `gpt-5.6-terra` (balanced — дефолт конфига), `gpt-5.6-sol` (frontier — тяжёлые задачи). Пример: `codex exec -m gpt-5.6-luna "..."`. НЕ использовать `gpt-4o`. Если падает `usage limit` — это дневной кап ВСЕГО аккаунта, смена модели не лечит. Полный гайд: скил `codex-cli-windows`, `autonomous-ai-agents/codex-cli-windows/references/model-inventory-usage-inspection.md`.

## Pitfalls (уроки портирования — не наступай снова)

- **Не делай из `/cursor` просто каталог-обёртку.** Пользователь явно хотел
  реальные портированные скиллы (по одному на каждый источник `SKILL.md`), а не
  абстракцию, которую надо раскрывать вручную. Форма: диспетчер `cursor` +
  78 самостоятельных портов в `skills/<plugin>-<skill>/`.
- **«Применяй все по очереди» ≠ гоняй все 78 скиллов.** Фраза «все» значит
  «все *применимые* к этому репо». Фильтруй по структуре репо (язык, тесты, CI,
  MCP, CLI) и ставь в фазовый порядок: понимание → аудит (read-only) → чистка →
  тесты/верификация → CLI/интеграции → доки/визуализация → PR. Не запускай
  `cursor-sdk` (TS-only), `teaching`, `create-plugin`, `ralph-loop`, `orchestrate`,
  `benny-*`, `looper` (если цикл не нужен) на Python-проект — они туда не ложатся.
- **Каждый порт обязан нести блок «Адаптация под Hermes».** Без него Cursor-
  специфика (subagents→delegate_task, hooks→cronjob/terminal, slash→native)
  сломается в Hermes.
- **Индекс перегенерируй при добавлении портов** — иначе роутер ослепнет на
  новые скиллы. Нативные скиллы (`deepseek-harness`) в генерируемый
  `_cursor_index.md` НЕ попадают — их маршруты живут в теле этого SKILL.md
  (раздел «Нативные (не-портированные) скиллы в роутинге»), не забывай их там.
- Рецепт портирования — в `references/porting-recipe.md`.

## Safe iterative remediation (Python repos)

When `/cursor` drives a multi-fix audit-remediation sequence:

1. **One defect class at a time.** Read the complete affected function/module before editing; state the precise acceptance contract before a patch.
2. **Keep structural edits atomic.** For indentation-sensitive Python functions, replace the complete function body in one patch rather than stacking several partial indentation patches. Immediately run `python -m py_compile <changed files>` before touching the next issue.
3. **Do not weaken the test suite to manufacture green.** Keep a failing regression test until the implementation is fixed; never delete a new test merely because it exposes an unfinished fix. If an integration test is environment-dependent, mark/skip it with an explicit reason only after preserving deterministic unit coverage.
4. **Verify before commit.** Run targeted regression tests, then the full relevant suite. If any failures are pre-existing, demonstrate that with the baseline or clearly report them; do not claim a clean suite otherwise.
5. **Preserve working APIs when reconstructing a damaged file.** A full-file rewrite is a last resort. First compare exports, CLI subcommands, native/legacy backends, and callers; after rewrite, compile and run the commands/tests that exercise each preserved interface.
6. **Push gate.** The standing default is local commits only. Push to `main` only when the user explicitly authorizes publishing for the current remediation sequence (e.g. "все фиксы по порядку" after an established direct-main workflow). Report each pushed commit and remote sync state.

### Audit remediation checkpoint

After every completed defect class, update the plan/status with: issue ID, files changed, targeted verification, full-suite result, and whether the change is committed/pushed. If a fix attempt leaves the worktree syntactically broken, stop the planned sequence, repair compilation first, then resume.

## Pitfall: review findings must be revalidated

Audit PRs frequently refer to an earlier SHA. Before implementing each listed finding, inspect the current target code and test the claimed path. Mark already-fixed or disproven findings in the remediation plan rather than applying duplicate fixes.

## Pitfall: static audit claims must be verified against live code

A detailed audit can claim wiring/factory/config breaks that look plausible on a GitHub raw-view but do not survive a single `pytest` or `inspect.signature` on the actual checkout. Before treating an audit finding as a P0 blocker, verify:
1. Read the actual module where the claimed mismatch lives (not the GitHub URL).
2. Run the specific test file the audit claims will fail.
3. Load the config and call the factory/coordinator from a Python script.
4. If the finding disproves — mark it as "not a bug, audit artifact" and move on. Do not apply fictional fixes to make the audit happy.

## Pitfall: argparse Namespace vs attribute access in CLI tools

When a CLI command crashes with `AttributeError: 'Namespace' object has no attribute 'exists'`, the cause is almost always passing the whole `args` Namespace into a helper that expects a `Path`. Fix: pass the specific attribute, e.g. `_resolve_capsule(args.capsule)` instead of `_resolve_capsule(args)`. Audit all subcommands after fixing—this bug tends to repeat across every command that uses the same helper.
