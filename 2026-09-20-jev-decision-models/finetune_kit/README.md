# Дообучение mmBERT (laya) на своих письмах: полный конвейер

Комплект к статье "Любовь - это русские придумали, чтобы денег не платить, или как всё-таки добить бесплатных Бертов до платного Jev".

Замерено на RTX 4060 8 ГБ: 1000 писем - 82 секунды тренировки, 10 000 - 15.5 минуты, пиково 3.6 ГБ VRAM. Тест: accuracy 0.427 (случайная голова) -> 0.873 (1k) -> 0.959 (10k), ECE 0.032.

> Сноска: вся эта затея - про любовь к инженерным экспериментам. Ни один шаг ниже не является "продакшн-решением по клике": это честный протокол, который можно повторить за вечер и понять, как это работает изнутри.

## Что делает каждый скрипт

```
01_fetch_imap.py    выгрузка писем по IMAP (тема + домен + тело 1500 знаков)
02_label_rules.py   слабая разметка правилами по доменам (бесплатно, ~35% потока)
03_label_llm.py     разметка остатка ротатором бесплатных LLM (OpenRouter :free)
                    429/503 -> автопереезд на следующую модель
04_train.py         дообучение mmBERT-энкодера из laya + голова на 2 класса
05_infer.py         инференс: p(важное) для одного письма
```

## Быстрый старт (для агента или человека)

Требования: python 3.11, pip install torch transformers safetensors huggingface_hub (USE_TF=0).
Креды: env IMAP_HOST, IMAP_USER, IMAP_PASS (Gmail - app-password), OPENROUTER_API_KEY.

```bash
# 1. выгрузить письма (равномерная выборка из INBOX)
python scripts/01_fetch_imap.py --limit 10000 --out mails.json

# 2. правила по доменам (отредактируйте NOISE/ACTION под свой ящик!)
python scripts/02_label_rules.py --mails mails.json --out mails_rules.json

# 3. ротатор бесплатных моделей для остатка (перед полным прогоном - smoke на 10!)
export OPENROUTER_API_KEY=sk-or-...
python scripts/03_label_llm.py --mails mails_rules.json --out mails_labeled.json

# 4. тренировка (энкодер laya подготовится сам из кеша HF; при первом запуске
#    веса скачаются: huggingface-cli download convaiinnovations/laya --include "multilingual/*")
python scripts/04_train.py --data mails_labeled.json --laya-dir <snapshot>/multilingual --out best_model

# 5. проверить
python scripts/05_infer.py --model best_model --text "Счёт за хостинг\nВаш счёт на июль..."
```

## Подводные камни (все набиты лично)

1. **USE_TF=0 обязателен** до импорта transformers - иначе TensorFlow-ветка laya виснет.
2. **Конфиг laya нестандартный**: веса в схеме encoder.*/act_head/scorer. 04_train.py сам переименует encoder.* в modernbert.* и выкинет головы RL-агента (см. prepare_laya_encoder).
3. **Reasoning-модели в ротаторе**: ответ приходит в поле reasoning, а content пустой - парсер extract() ищет да/нет в обоих.
4. **max_tokens=300**: reasoning-модели тратят токены на размышления, при 10-40 ответ обрезается до пустоты.
5. **429 - это норма**: ротатор просто переезжает на следующую модель; статистика из статьи - сотни переходов, потери 3.4%.
6. **Дисбаланс классов** (12:1): accuracy врёт, смотрите F1 и ECE. Модель "всем не важно" даёт 0.91 accuracy и ноль пользы.
7. **Специализация необратима**: модель, дообученная на важности писем, разучивается ловить инъекции (18/20 -> хуже случайного). Одна задача - одна модель, для N задач - N датасетов.

## Пайплайн из нескольких специализаций

Протокол повторяем для любой задачи. Память на RTX 4060: одна mmBERT bf16 = 0.57 ГБ, int8 = 0.29 ГБ; 10 моделей bf16 = 5.7 ГБ (влезает), на CPU - хоть двадцать. Цепочка из пяти моделей по 20-40 мс быстрее одного вызова локальной 8B.

## Лицензии и благодарности

- [laya / Convai Innovations](https://huggingface.co/convaiinnovations/laya) - Apache 2.0, сами веса и идея
- [OpenRouter](https://openrouter.ai) - бесплатный tier для разметки
- Замеры и текст: @hermesagentru, [hermes-agent.ru](https://hermes-agent.ru)
