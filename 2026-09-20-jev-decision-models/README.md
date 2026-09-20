# Jev vs открытые модели решений: код и данные всех частей серии

Материалы к серии статей @hermesagentru:
- Часть 1 (пост 239): "Три эвала для модели решений: Jev против локальной 8B" - https://telegra.ph/Tri-ehvala-dlya-modeli-reshenij-Jev-protiv-lokalnoj-8B-09-19
- Часть 2 (пост 240): "Матрица Эйзенхауэра на модели решений" - https://telegra.ph/Matrica-EHjzenhauehra-na-modeli-reshenij-chast-2-09-19
- Часть 3 (пост 241): "Открытая альтернатива Jev: два чекпоинта laya на русских эвалах" - https://telegra.ph/Otkrytaya-alternativa-Jev-dva-chekpointa-laya-na-russkih-ehvalah-09-20
- Часть 4: "Любовь - это русские придумали, чтобы денег не платить: добиваем бесплатных Бертов до платного Jev" - https://telegra.ph/Kak-ya-doobuchil-otkrytuyu-model-na-desyati-tysyachah-svoih-pisem-09-20

## Структура

```
part1-triage_jev_vs_8b.md      статья части 1 (текст)
part2-eisenhower.md            статья части 2 (текст)
part3b-laya-checkpoints.md     статья части 3 (текст, испр. копия + эпилог)
part3-theory_finetune.md       теория дообучения + замер 4 систем (введение в часть 4)
part4-protocol_10k.md          статья части 4 (текст)
jev_client.py                  клиент TypeSafe Jev: jev_ask/jev_batch/jev_triage,
                               ретраи 429/529, пин jev-1.13.0
run_evals.py                   воспроизведение эвалов: инъекции, реранкер, почта
laya_eisenhower.py             матрица Эйзенхауэра на laya: fan-out 2 noul,
                               4 квадранта + зона "человеку", Platt, ECE
evals/                         сеты: инъекции (10+10), реранкер (6+6),
                               25 заголовков, 15 писем с метками (обезличено)
finetune_kit/                  ПОЛНЫЙ конвейер дообучения (к части 4):
                               01_fetch_imap, 02_label_rules, 03_label_llm (ротатор),
                               04_train, 05_infer + README с граблями
results/all_results.json       все метрики: bench150 (4 системы),
                               finetune 1k vs 10k, регрессия на 3 эвалах
```

## Запуск эвалов (части 1-3)

```bash
pip install laya            # открытая модель, CPU
export TYPESAFE_API_KEY=... # только для Jev-частей

python run_evals.py B_jev   # инъекции через Jev
python run_evals.py B_laya  # инъекции через laya локально
python run_evals.py E       # матрица на письмах
```

## Запуск дообучения (часть 4)

```bash
cd finetune_kit
# по шагам: см. finetune_kit/README.md
# кратко:
python scripts/01_fetch_imap.py --limit 10000 --out mails.json
python scripts/02_label_rules.py --mails mails.json --out mails_rules.json
python scripts/03_label_llm.py --mails mails_rules.json --out mails_labeled.json
python scripts/04_train.py --data mails_labeled.json --laya-dir <snapshot>/multilingual --out best_model
python scripts/05_infer.py --model best_model --text "Счёт за хостинг..."
```

Замерено на RTX 4060 8 ГБ: 1к писем = 82 с, 10к = 15.5 мин, пиково 3.6 ГБ.

## Ключевые цифры (русские сеты, 2026-09-20)

Эвалы (части 1-3):

```
                  Jev API   8B лок.  laya-en  laya-mm
инъекции (20)     19/20     17/20    14/20    18/20
реранкер (12)     12/12     11/12    10/12     9/12
сотня писем       13.4с      -        3.1с     1.7с
```

Дообучение (часть 4):

```
                    1k писем   10k писем   base
accuracy             0.873      0.959      0.427
F1 важного           0.537      0.725      0.187
ECE                  0.095      0.032      0.317
время                82 с       15.5 мин     -
```

bench150 (150 писем, 4 системы): Jev 0.90/0.839/ECE 0.037/12с;
8B 0.75/0.661/-/72с; mmBERT base 0.52/0.294/0.317/2.2с; mmBERT fine-tuned 0.89/0.795/0.102/0.95с.
Все метрики и история обучения - `results/all_results.json`.

Калибровка (Platt, 32 метки): laya-mm ECE 0.161 -> 0.083; laya-en ложные Q1 11 -> 2.
Laya поставляется переуверенной - перед доверием вероятностям калибруй на своей разметке.

## Приватность

Письма в evals/ обезличены (тема обрезана, домен, вердикт - без текста писем и адресов).
Полные тексты писем в finetune_kit НЕ входят: 01_fetch_imap.py качает их к тебе локально.
Jev - закрытый API (данные уходят наружу); laya - локально. ZDR у TypeSafe только на enterprise.

## Зеркала

- GitHub: https://github.com/NikolayGusev-astra/channel-materials
- GitFlic: https://gitflic.ru/manve-sulimo2/channel-materials
