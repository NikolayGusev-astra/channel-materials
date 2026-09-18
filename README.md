# channel-materials

Материалы канала [@hermesagentru](https://t.me/hermesagentru): статьи, харнессы для тестов, артефакты.

Каждая публикация канала - папка `ГГГГ-ММ-ДД-slug/` со статьёй и приложенными материалами. Список ниже обновляется при публикации.

Зеркала: [GitHub](https://github.com/NikolayGusev-astra/channel-materials) | [GitFlic](https://gitflic.ru/manve-sulimo2/channel-materials)

## Материалы

| Дата | Материал | Что внутри |
|------|----------|------------|
| 2026-09-18 | [Bonsai 2 27B на RTX 4060: замер скорости, качества и контекста](./2026-09-18-bonsai2-27b-4060/) | замер тернарной 27B (PrismML) на 8 ГБ VRAM: 38 задач, 64к контекст, статья + харнесс (bench_local.py, grade_local.py) + инструкция запуска llama-server от PrismML + сырые результаты; вторая часть (128к, medium) в работе |
| 2026-09-15 | [YandexGPT и GigaChat: 38 задач в одном замере](./2026-09-15-yandexgpt-gigachat-38-tasks/) | замер 8 русских моделей (YandexGPT-5-Lite/5.1-Pro + 6 GigaChat), 76 яндексовских прогонов, статья + харнессы (yandex_bench.py, bench_runner.py) + сырые результаты всех моделей |
| 2026-09-12 | [SKILL.state vs ReAct vs compress+search](./2026-09-12-skill-state-bench/) | замер управления контекстом на LFM2.5-8B-A1B: bench-скрипты, логи прогонов |
| 2026-09-12 | [На opencode раздают GLM-5.5?](./2026-09-12-omen-alpha-glm55-fingerprint/) | проверка фингерпринта анонимного провайдера, статья + скрипты + данные |
| 2026-09-12 | [Русский токенизатор GigaChat против open-моделей](./2026-09-12-gigachat-open-bench/) | замер 519 живых запросов, 14 моделей, статья (2 редакции) + харнесс бенча |
| 2026-09-07 | [Model-Routing: как AI-агент выбирает модель под задачу](./2026-09-07-model-routing/) | статья + картинки, lm-studio-тесты, article-habr редакция |
| 2026-09-07 | bonus4: Нук аэропорт-бутлег-бандл (не статья) | сборное: character/, nova/, prompts/, styles/, download-bonus4-bundle.py + README-install.md |
| 2026-09-05 | [Бенчмарки врут красиво: 6 локальных моделей под 8 GB VRAM](./2026-09-05-local-models-8gb/) | статья + мини-харнесс: 7 карточек моделей (Ling-3.0-tiny, Ornith-1.5-9B, Aion-RP, AgentFlow planner, CogEvol-4B, Apollo-4B-Thinking + бонус LFM2.5-VL-3B / Granite-4.1-3B) с ссылками на кванты, параметрами LM Studio и заданиями с критериями прохода |
| 2026-09-05 | bonus2: комикс-исходники (не статья) | панели и постеры: neznaika-strip-v2/v3, bonus3-* сравнения, canon.jpg |
| 2026-09-19 | [Bonsai 2 в пайплайне: история одного разочарования](./2026-09-18-bonsai2-27b-4060/article_part2.md) | вторая часть: prefill-предел агентского хода, роли в пайплайне |

## Формат папки

```
YYYY-MM-DD-slug/
  article.md      - текст статьи (источник истины)
  harness/        - приложения: харнессы, конфиги, задания
  artifacts/      - сгенерированные артефакты (если были)
```

## Лицензия

Материалы распространяются по [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ru) с указанием авторства. Код и конфиги в приложениях - [MIT](./LICENSE) если не указано иное.
