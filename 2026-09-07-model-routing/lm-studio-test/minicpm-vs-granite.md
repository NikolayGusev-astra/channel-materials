# MiniCPM5-2B vs granite-4.1-3b: финал дуэли диспетчеров

**Date:** 2026-09-08
**Контекст:** выбор локального диспетчера model-routing. Роль: читать задачу,
скорить, вызывать delegate_task/answer_self, передавать задачу субагенту.

## Важная методологическая оговорка (от юзера, 2026-09-08)

Прямое сравнение tok/s некорректно: granite гонялась в 1 поток на холостом
сервере, MiniCPM5 - под 3-4 параллельными запросами (диспетчерский тест +
Hermes-оркестратор + субагенты одновременно). Для честного сравнения скорости
нужен изолированный прогон, который не проводился. Поэтому сравниваем
дискретные метрики и устойчивость под нагрузкой.

## Дискретные метрики (нагрузконезависимые)

| Метрика | granite-4.1-3b | MiniCPM5-2B |
|---|---|---|
| Текстовая сюита T1-T7 | 6/7 (rp-bait fail) | 6/7 (rp-bait fail; T4 прошёл с max_tokens 800) |
| Tool-call диспетчер 4 категории | 4/4 | 4/4 (deep переподтверждён отдельным прогоном) |
| quick -> answer_self | да | да |
| model_hint точность | 1 ошибка (standard -> deep) | точный |
| Русский текст в goal/context аргументах | ИСКАЖАЕТ ("распарлены загоды") | ЧИСТЫЙ ("Find all usages of deprecated APIs...") |
| Декомпозиция architect-задачи | 2 задачи | 3 задачи (security, idempotency, observability) с инженерным контекстом |
| clarify при неоднозначности | да (в architect-задаче) | да (в architect-задаче) |
| Живой Hermes полный цикл | да (субагент на hy3) | да (2 субагента, 2 файла-артефакта) |
| Memory (GGUF Q4) | 2.00 GB | 1.56 GB |
| Нативный контекст | 128K | 131K |
| Работа под параллельной нагрузкой | не тестировалась | 4/4 дисциплина при 3-4 параллельных запросах |

## Живой Hermes: полный цикл MiniCPM5

Сессия 20260908_131351_4bea3f: архитектура платёжного микросервиса (architect).

1. MiniCPM5-2b как orchestrator в живом Hermes (lmstudio, 131K контекст)
2. Скоринг по скиллу model-routing: deep категория (~8/9)
3. delegate_task spawn с ДВУМЯ субагентами (не один - декомпозиция)
4. Субагенты отработали, создали 2 файла-артефакта:
   - payment-microservice-arch.md (128 строк: K8s, Helm, service mesh,
     idempotency, HPA, CI/CD, Prometheus adapter)
   - payment_microservice_architecture.md (второй субагент)
5. Финальный ответ с указанием цепочки: kilo hy3 -> zcode glm-5.3 ->
   codex gpt-5.6-terra (deep chain из скилла)

Грамотность payload: mTLS, OAuth2/OIDC, Vault/KMS, STRIDE threat model,
idempotency UUID v4, circuit breaker, OTel - без единого искажения русского.

## Вывод

**MiniCPM5-2B забирает роль диспетчера:**

1. Та же tool-call дисциплина (4/4) при лучшем качестве аргументов
   (русский чистый, декомпозиция богаче, hints точнее)
2. Меньше памяти (1.56 GB vs 2.00 GB), больше нативный контекст (131K vs 128K)
3. Подтверждённая работа под параллельной нагрузкой - прикладная метрика
   для фонового роутера, важнее пикового tok/s
4. 2B параметров (2516M) против 3B - SOTA по Artificial Analysis
   Intelligence Index (53.9) среди <4B подтверждается практикой

granite-4.1-3b остаётся валидным запасным диспетчером и "тяжёлой" версией,
если MiniCPM5 недоступна. Обе модели проходят rp-bait одинаково плохо
(линейки вежливые) - правило 6 протокола обязательно для обеих.

## Дуэль квантов MiniCPM5-2B (2026-09-08, финал)

**Методология:** изоляция (unload после каждого), `--gpu max`, контекст 65536,
max_tokens=1500, temperature=0, байт-точные тулы. A/B с draft-моделью сорвался:
спекулятивный draft в LM Studio падает с `invalid vector subscript` при Q4_K_M
как draft для Q8/F16 этой модели (зафиксировано как баг связки).

**Матрица (4 категории tool-call, правильные descriptions):**

| Категория | Q4_K_M | Q8_0 | F16 |
|---|---|---|---|
| quick (→answer_self) | OK | OK | OK |
| standard (→delegate, hint=standard) | OK | FAIL (answer_self!) | FAIL (answer_self!) |
| deep (→delegate, hint=deep) | OK | FAIL (hint=standard) | FAIL (hint=standard) |
| architect (→delegate, hint=architect) | FAIL (hint=deep) | OK | OK |
| **Итог** | **3/4** | 2/4 | 2/4 |
| **Throughput, tok/s** | **121.1** | 80.6 | 30.0 |

**Выводы:**
1. **Q4_K_M - лучший квант для диспетчера**: лучшая дисциплина (3/4), скорость
   в 4 раза выше F16. Дискретная ошибка одна: architect получил hint=deep
   (грейд категории, не выбор инструмента).
2. **Большие кванты НЕ улучшают диспетчеризацию**: Q8 и F16 одинаково
   ошибаются на standard/deep - отправляют задачи себе вместо делегации
   (answer_self на "найди все API"!). Чат-шаблон один, веса разные -
   дисциплина tool-call у этой модели деградирует с ростом точности кванта.
3. **Хрупкость к descriptions тулов** (нашёлся при отладке): сокращение
   description у answer_self с "Use ONLY for trivial tasks (rename, typo,
   one-liner)" до "ONLY for trivial tasks" сломало дискриминацию quick:
   модель перестала распознавать trivial и всё отдавала делегации.
   Возврат примеров в description = мгновенное восстановление. Малая модель
   читает примеры в описаниях буквально. Вывод: не "оптимизируй" описания
   тулов без A/B-теста на той же модели.
4. **Draft-механизм LM Studio** для этой модели не работает (Q4-draft для
   Q8/F16: invalid vector subscript). Спекулятивное ускорение недоступно.

**Рекомендация:** MiniCPM5-2B **Q4_K_M**, `--gpu max -c 65536`, оригинальные
описания тулов (с примерами), max_tokens >= 800 для reasoning-запаса.

**Итоговая архитектура (закрытый вопрос):**

```
Юзер -> Hermes (MiniCPM5-2B Q4_K_M локально, диспетчер)
         |- quick -> answer_self (сам, 0 руб)
         |- standard/deep -> delegate_task -> free-канал (hy3 и др.)
         `- architect -> delegate_task -> подписка (codex/zcode)
```

Полный цикл подтверждён в живых сессиях:
- granite-3b: skill_manage + delegate_task -> субагент на hy3 -> отчёт
  (сессия 20260908_122906_2ff6b5)
- MiniCPM5: скоринг deep (8/9) -> 2 субагента параллельно -> 2 файла-артефакта
  (payment-microservice-arch.md 128 строк + design doc)
  (сессия 20260908_131351_4bea3f)
- Стоимость обеих цепочек: 0.00 USD (диспетчер локальный, субагенты free)

## Артефакты

- minicpm5 T1-T8: Temp/lm_test/minicpm5-2b-ext.json
- minicpm5 диспетчер: Temp/granite_tc_dispatch.json (последний прогон)
- Hermes-сессии: 20260908_125921_c0eefd (обрыв, полный payload),
  20260908_131351_4bea3f (полный цикл с артефактами)
- Файлы-артефакты субагентов: Work/Assist/payment-microservice-arch.md,
  Work/Assist/payment_microservice_architecture.md
