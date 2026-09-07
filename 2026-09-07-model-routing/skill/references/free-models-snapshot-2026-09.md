# Свежие живые данные free-пулов (snapshot 2026-09-07)

Эти данные устаревают — перепарси каталоги командами из §8 SKILL.md.
Vendor-бенчи и независимые замеры **несопоставимы**, не мешай.

## Kilo — 15 free моделей + terminal-bench

Источник: `curl -s https://kilo.ai/api/models` (поля `priceInput==0` и
`benchmarks.kiloBench.terminal-bench.overallScore`). Kilo — единственный
провайдер, который гоняет стандартизированный terminal-bench на живых
моделях (445 trials, своя версия harness).

| Модель | ctx | tb (kilo) | Применимость |
|---|---|---|---|
| tencent/hy3 | 256K | **47.6%** | код, агенты, general — лучшая free |
| minimax/minimax-m3 | 1M | 47.6%* | мультимодальная, long-context, *платный замер |
| thinkingmachines/inkling | 1M | 43.6%* | general + tools + mm, *платный замер |
| poolside/laguna-s-2.1 | 256K | 31.0% | чистый кодинг (vendor 70.2% — другая версия бенча) |
| poolside/laguna-xs-2.1 | 256K | 26.7% | мелкий код-рутин |
| nvidia/nemotron-3-ultra-550b | 1M | 19.1% | orchestration, 1M ctx; **НЕ для кода** |
| nvidia/nemotron-3-super-120b | 256K | 15.5% | high-throughput рутина |
| baidu/cobuddy | ? | 1.1% | **НЕ ИСПОЛЬЗОВАТЬ** |
| google/gemma-4-26b-a4b-it | 256K | — | мультимодальная, проза |
| google/gemma-4-31b-it | 256K | — | мультимодальная dense, проза |
| inclusionai/ling-3.0-flash | 256K | — | быстрая рутина, низкая цена |
| inclusionai/ling-2.6-1t | 256K | — | альтернатива ling-flash |
| inclusionai/ling-2.6-flash | 256K | — | лёгкий код |
| inclusionai/ring-2.6-1t | 256K | — | ring-вариант ling |
| tencent/hy3-preview | 256K | — | preview tencent, может уйти |
| nex-agi/nex-n2-pro | 256K | — | nex-агент |
| openrouter/pony-alpha | 200K | — | экспериментальный OpenRouter |
| nemotron-3.5-lightning | ? | — | nemotron-lightning |

## OpenRouter — 18 free моделей

Источник: `curl -s https://openrouter.ai/api/v1/models | jq '.data[]|select(.id|endswith(":free"))'`.
Пул совпадает с Kilo по основным моделям, плюс ротация:
dots-studio/dots-3-note-preview, north-mini-code, nemotron-3-5-content-safety,
inclusionai/ling-3.0-flash-sante/fin (специализированные варианты), и т.д.

## Nous Portal — каталог 41 модель, free-тир = подписка $0

Источник: `curl -sL https://hermes-agent.nousresearch.com/docs/api/model-catalog.json`.
Каталог питается OpenRouter, но **free-тир определяется живой ценой портала**
(`partition_nous_models_by_tier`), а не манифестом. Лимиты free-тира:
**50 RPM / 500K TPM**, Plus $20/мес → 400 RPM / 4M TPM. Прямой вызов через
`inference-api.nousresearch.com/v1/models` — требует Nous Portal API key
(сейчас не сконфигурирован в `~/.hermes/.env`).

### Hermes-курированный free-пул (10 моделей, приоритет над OR-общим)

Подмножество OR-общего free-пула, отфильтрованное командой Hermes. Брать
предпочтительнее, чем сырой OR-список: модель точно живая, лимиты предсказуемые,
не зависишь от ротаций. Помечено `description: "free"` в `model-catalog.json`.

| Hermes-id | ctx | Kilo tb | Для чего |
|---|---|---|---|
| `thinkingmachines/inkling:free` | 1M | 43.6% (платн.) | general, mm, long ctx |
| `thinkingmachines/inkling-small:free` | 1M | — | быстрая general/mm |
| `minimax/minimax-m3:free` | 1M | 47.6% (платн.) | long-horizon, mm, агенты |
| **`z-ai/glm-5.2:free`** | ? | — | general — **только через Hermes-ключ**, в OR `/api/v1/models` НЕТ |
| `poolside/laguna-s-2.1:free` | 256K | 31.0% | код-агент |
| `poolside/laguna-xs-2.1:free` | 256K | 26.7% | мелкий код |
| `nvidia/nemotron-3-super-120b-a12b:free` | 256K | 15.5% | рутина |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | 1M | 19.1% | orchestration, НЕ код |
| `nvidia/nemotron-3.5-lightning:free` | 1M | — | high-throughput |

Что **нет** в Hermes-курированном, но есть в OR-общем: `tencent/hy3:free` (47.6% tb,
лучшая free код), `google/gemma-4-31b-it:free`, `inclusionai/ling-3.0-flash:free`. Эти
три — только через OR-ключ.

## Калибровка платных моделей (kilo terminal-bench, для контекста)

| Модель | price_in | tb |
|---|---|---|
| openai/gpt-6-astra | 10.00 | 79.3% |
| openai/gpt-5.6-sol | 4.00 | 76.2% |
| anthropic/claude-fable-5.1 | 10.00 | 76.2% |
| google/gemini-3.8-flash | 0.75 | 75.3% |
| openai/gpt-5.5 | 5.00 | 74.2% |
| x-ai/grok-4.6 | 2.00 | 73.0% |
| moonshotai/kimi-k3 | 3.00 | 72.8% |
| z-ai/glm-5.2 | 1.40 | 53.0% |
| qwen/qwen3.8-max | 2.00 | 54.2% |

Граница «free-уровень» по этому бенчу: 47.6% (hy3) ≈ 53% (glm-5.2 платный).
Лучшая free **не дотягивает** до frontier (76%+). Эскалация на codex/sol
оправдана для architect/ultrabrain; для deep — hy3 часто хватает.

## Что путается в головах агентов

- **«Nous Portal» ≠ «nous/free».** Nous Portal — это подписочная платформа
  с квотой $5 на старте. Free-тир там даёт список моделей по живой цене,
  а не по манифесту. Просто «nous/free» — выдумка, в API не существует.
- **«zcode/glm-flash» не существует.** Реальный список: `glm-5.3`, `glm-5.2`,
  `glm-5-turbo` (в config.json). Команда `zcode.cjs --model X` не работает —
  модель только через config.json.
- **`z-ai/glm-5.2:free` есть в Hermes-каталоге, НО нет в OpenRouter.** У Hermes
  это `description: "free"`, у OR `/api/v1/models` такой модели нет. Если
  юзер ходит через `inference-api.nousresearch.com` (Hermes-ключ) —
  доступна с предсказуемыми лимитами 50 RPM / 500K TPM. Через OR-общий
  ключ — её в пуле нет, роутер её не предлагает.
- **«OpenRouter/что-то» ≠ «OpenRouter auto-router».** `openrouter/free` —
  это авто-роутер по free-пулу, не отдельная модель. В цепочках его
  указывать не надо, он сам выберет.
- **vendor-бенч ≠ независимый замер.** Laguna vendor 70.2% TB2.1 vs kilo 31%
  TB-kilo — обе правды, разные харнесы. Сравнивай только в одном источнике.
- **`codex exec` — не провайдер для прямого вызова, а субагент-делегация.**
  Цепочка `codex/terra → zcode/glm-5.3 → hy3:free` подразумевает «прыжок
  между провайдерами в текущем вызове», которого нет. Каждый «прыжок» =
  новый `delegate_task`, минуты ожидания, новый токен-пул. В одной сессии
  у тебя одно активное место исполнения, не три модели параллельно.
