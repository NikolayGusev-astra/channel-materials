# Харнесс тестов EXL3 (статья EXL3-2)

Инструменты из статьи «EXL3-2: тысяча квантов, один подходит».

## Состав

- `scan-exl3-catalog.py` - сканер EXL3-каталога HuggingFace: кодбук, архитектура,
  параметры, скачивания для живых релизов. Результат - JSON для отбора кандидатов.
- `check-codebook.sh` / `.ps1` - быстрая проверка кодбука одного релиза перед закачкой.
- `bench3.py` - по-токенный замер ExLlamaV3 (TTFT, фазы, скорость декода).
  Настраивается под модель: MODEL_DIR в шапке файла.
- `exl3-catalog-scan.json` - результат скана каталога на 2026-10-03 (223 живых релиза).

## Быстрая проверка кодбука перед закачкой

```bash
curl -sL https://huggingface.co/<repo>/resolve/<branch>/quantization_config.json | grep codebook
```

mul1 = CPU-offload будет работать. mcg = движок молча оставит экспертов на GPU.

## Скан каталога

```bash
python scan-exl3-catalog.py --min-downloads 100 --top 250 --out scan.json
```

12 потоков, 223 репозитория ~ 13 секунд. Фильтры после скана: codebook == mul1,
moe == true, размер весов против бюджета (VRAM + RAM - 8 ГБ на систему).

## Замер модели

1. Поставить PyTorch с CUDA и ExLlamaV3 (prebuilt wheel из releases под свою связку).
2. В bench3.py прописать MODEL_DIR.
3. `python bench3.py --mcl 40 --max-new 64` - events покажут TTFT и темп по токенам.

## Протокол ресурсов

Перед каждым прогоном: `nvidia-smi` (VRAM free) и FreePhysicalMemory (RAM free).
Если веса + активации не влезают в VRAM + usable RAM без остатка - генерация пойдёт
через pagefile: скорость упадёт на порядки, SSD начнёт читать сотни МиБ на токен.
