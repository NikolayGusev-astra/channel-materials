---
name: pstack-principles
description: "Use when проектируешь, ревьюишь или дебажишь код — принципы."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, design, debugging, refactoring, principles]
---

# pstack-principles — 21 принцип pstack одним зонтиком

Ситуация → принцип → чек-лист. Принципы портированы из cursor/pstack. Оригиналы лежат в `.archive/skills-2026-10-07/pstack-principle-*` — полный текст принципа открывается оттуда. Зонтик создан потому, что 14 из 21 принципа не открывались ни разу за 90 дней: дискрипторы-одиночки не выстреливали.

## Как пользоваться

1. Найди в таблице ситуацию, похожую на твою.
2. Открой `.archive/skills-2026-10-07/pstack-principle-<имя>/SKILL.md` — там полный чек-лист.
3. Примени его к текущей задаче.

## Таблица: ситуация → принцип

| Ситуация | Принцип |
|---|---|
| Пишешь валидацию, обработку ошибок, адаптеры фреймворков | boundary-discipline |
| Любая нетривиальная работа — с чего начать | build-the-lever |
| Ловишь себя на повторе одной и той же инструкции | encode-lessons-in-structure |
| Новое UI-взаимодействие или архитектурное решение без прецедента | exhaust-the-design-space |
| Трейдоффы по продукту, UX, объёму фичи | experience-first |
| Дебаг: симптом | fix-root-causes |
| Перед написанием логики: выбор структур и контрактов | foundational-thinking |
| Контекст заполняется: большие выводы, длинные файлы | guard-the-context-window |
| Рефакторинг, оценка размера диффа, соблазн добавить абстракцию | laziness-protocol |
| Проектируешь команды, lifecycle-шаги, обработку повторов | make-operations-idempotent |
| Вводишь новый внутренний API рядом со старым | migrate-callers-then-delete-legacy-apis |
| Код трудно трассировать, ревью читателя | minimize-reader-load |
| Стейтфул-логика, много ветвлений и повторов | model-the-domain |
| Хочешь спросить «делать ли X?» на обратимой работе | never-block-on-the-human |
| Плановое переписывание или миграция | outcome-oriented-execution |
| Задача завершена, до объявления готовности | prove-it-works |
| Новое требование вливается в существующую систему | redesign-from-first-principles |
| Конкурентные акторы пишут в общее состояние | separate-before-serializing-shared-state |
| Многошаговая работа (свипы, миграции, деплои) | sequence-verifiable-units |
| Планируешь добавление, рефакторинг или переписывание | subtract-before-you-add |
| Проектируешь типы, ревьюишь сигнатуры | type-system-discipline |

## Ключевые правила (выжимка самых используемых)

- **fix-root-causes**: каждый симптом трассируй до корня, чини причину, не симптом.
- **prove-it-works**: «готово» — только с фактическим прогоном, не описанием того, что было бы.
- **make-operations-idempotent**: повтор идемпотентной операции = NO-CHANGE, не второй успешный прогон.
- **subtract-before-you-add**: перед добавлением нового — что можно вычесть.
- **never-block-on-the-human**: обратимая работа — делай, а не спрашивай.
- **guard-the-context-window**: приоритизируй то, что попадёт в контекст; выкидывай шум.
