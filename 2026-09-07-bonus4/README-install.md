# Bonus 4 — README Install Guide for Agent

Цель: поднять локальный арт-стек (Krita 5.2 + AI Diffusion v1.53.0 + ComfyUI + 5 SDXL чекпойнтов + IP-Adapter) на чистой Windows-машине с 8 ГБ VRAM за ~30 минут скачивания и 5 минут ручной работы. На выходе — возможность рисовать 0 руб/кадр в любом стиле с любой скоростью.

## Предусловия

- Windows 10/11
- NVIDIA GPU с 8 ГБ VRAM (или больше)
- 50 ГБ свободного диска
- Python 3.11 (или conda с Python 3.11)
- Hugging Face доступ (для скачивания моделей)
- Интернет ~10 МБ/с (всё качается за ~30 мин)

## Шаг 0: проверка окружения

```bash
nvidia-smi          # проверить GPU и VRAM
python --version    # 3.11+
df -h               # 50 ГБ свободно
```

## Шаг 1: Krita 5.2.11 portable (2 мин)

**Не Krita 6.x** — плагин v1.53.0 не работает на Krita 6.

```bash
curl -L -o $LOCALAPPDATA/Temp/krita5.zip \
  "https://download.kde.org/Attic/krita/5.2.11/krita-x64-5.2.11.zip"
mkdir -p /c/Work/Assist/tools/krita5
cd /c/Work/Assist/tools/krita5 && unzip -oq $LOCALAPPDATA/Temp/krita5.zip
# бинарь: C:\Work\Assist\tools\krita5\krita-x64-5.2.11\bin\krita.exe
```

## Шаг 2: AI Diffusion v1.53.0 плагин (3 мин)

Скачать с GitHub:
```bash
curl -L -o $LOCALAPPDATA/Temp/krita-plugin.zip \
  "https://github.com/Acly/krita-ai-diffusion/releases/download/v1.53.0/krita_ai_diffusion-1.53.0.zip"
```

**Импортировать через UI, не копировать руками** (иначе docker не появится):
1. Запустить Krita 5.2.11.
2. Меню `Tools → Scripts → Import Python Plugin from File…` → выбрать ZIP.
3. На вопрос «Enable plugin?» — Yes.
4. **Перезапустить Krita** (обязательно).

После рестарта плагин лежит в `Tools → Scripts → AI Image Diffusion` и в меню `Настройка → Панели → AI Image Generation` появится docker.

## Шаг 3: ComfyUI (если ещё не стоит)

Из Бонуса 1: `comfyui/` с venv. Если есть — пропускаем. Иначе:
```bash
cd /c/Work/Assist
git clone https://github.com/comfyanonymous/ComfyUI.git comfyui
cd comfyui
python -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt
```

## Шаг 4: кастом-ноды (2 мин)

Плагин Krita требует две обязательные кастом-ноды, иначе «Missing required node»:
```bash
cd /c/Work/Assist/comfyui/app/custom_nodes
git clone --depth 1 https://github.com/Fannovel16/comfyui_controlnet_aux.git
git clone --depth 1 https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
```

`cv2` для `comfyui_controlnet_aux`:
```bash
/c/Work/Assist/comfyui/venv/Scripts/python.exe -m pip install opencv-python-headless
```

## Шаг 5: модели (25 мин скачивания)

Скрипт `download-bonus4-bundle.py` (см. ниже) качает всё нужное в правильные папки. Запускать **один раз**:

```bash
/c/Work/Assist/comfyui/venv/Scripts/python.exe "C:/path/to/download-bonus4-bundle.py"
```

Что качается (суммарно ~40 ГБ):

| Куда | Файл | Размер | HF repo |
|---|---|---|---|
| `checkpoints/` | novaAnimeXL_ilV125.safetensors | 7.1 ГБ | Acly/SD-Checkpoints |
| `checkpoints/` | RealVisXL_v5.0_fp16.safetensors | 6.9 ГБ | SG161222/RealVisXL_V5.0 |
| `checkpoints/` | JuggernautXL_v9_rdphoto2.safetensors | 7.1 ГБ | RunDiffusion/Juggernaut-XL-v9 |
| `checkpoints/` | DreamShaperXL_Turbo.safetensors | 6.9 ГБ | Lykon/dreamshaper-xl-turbo |
| `checkpoints/` | sd_xl_base_1.0.safetensors | 6.9 ГБ | stabilityai/stable-diffusion-xl-base-1.0 |
| `loras/` | Hyper-SDXL-8steps-CFG-lora.safetensors | 0.8 ГБ | Acly/SD-Checkpoints |
| `vae/` | sdxl_vae.safetensors | 0.3 ГБ | madebyollin/sdxl-vae-fp16-fix |
| `text_encoders/` | clip_l_sdxl_base.safetensors | 0.5 ГБ | stabilityai/stable-diffusion-xl-base-1.0 (text_encoder) |
| `text_encoders/` | clip_g_sdxl_base.safetensors | 2.8 ГБ | stabilityai/stable-diffusion-xl-base-1.0 (text_encoder_2) |
| `ipadapter/` | ip-adapter_sdxl_vit-h.safetensors | 0.7 ГБ | Acly/IP-Adapter |
| `clip_vision/` | clip-vision_vit-h.safetensors | 2.5 ГБ | h94/IP-Adapter |
| `inpaint/` | fooocus_inpaint_head.pth + inpaint_v26.fooocus.patch | 1.3 ГБ | lllyasviel/fooocus |
| `upscale_models/` | 4x_NMKD-Superscale-SP_178000_G.pth | 67 МБ | Kim2091/4x-UltraSharp |
| `upscale_models/` | OmniSR_X2/X3/X4_DIV2K.safetensors | 5 МБ | Acly/Omni-SR |
| `inpaint/` | MAT_Places512_G_fp16.safetensors | 125 МБ | Acly/MAT |

**Важно**: `curl` через корпоративный прокси отдаёт LFS-pointer 29 байт вместо файла. Скрипт использует `python urllib` с `User-Agent: Mozilla/5.0` — он пробивает. Если используешь другой сетевой стек — замени `urllib.request` на свой.

## Шаг 6: settings.json плагина Krita

Создать файл `%APPDATA%\krita\ai_diffusion\settings.json` (содержимое):
```json
{
  "server_mode": "external",
  "server_url": "http://127.0.0.1:8188"
}
```

`server_mode` — **строка**, не число. Число вызовет «Invalid value '1'» и откат на `undefined`.

## Шаг 7: запуск ComfyUI (1 мин)

```bash
cd /c/Work/Assist/comfyui/app
/c/Work/Assist/comfyui/venv/Scripts/python.exe main.py \
  --lowvram \
  --reserve-vram 0.5 \
  --disable-auto-launch \
  --listen 127.0.0.1 \
  --port 8188
```

Должно появиться: `To see the GUI go to: http://127.0.0.1:8188`. Проверить:
```bash
curl http://127.0.0.1:8188/system_stats
```

Должен вернуть JSON с `"comfyui_version"`.

## Шаг 8: подключение Krita к ComfyUI (1 мин)

1. Запустить Krita 5.2.11, открыть документ (`Ctrl+N`, `Использовать этот шаблон`).
2. `Настройка` (Alt+Н) → `Панели` (↓) → раскрыть (→) → кликнуть `AI Image Generation`.
3. В docker'е `Configure` → `Custom Server` → URL `http://127.0.0.1:8188` → `Connect`.
4. Если ошибка «Missing common models» — проверить что MAT и OmniSR скачаны (Шаг 5).
5. Кружок должен стать зелёным. В docker'е появится выбор модели (Nova Anime XL и др.) и поле промпта.

## Шаг 9: первый тест (30 сек)

Промпт: `a small red cat on a wooden table, soft window light, photo, 8k, sharp focus`

Стиль: `Photograph` (если есть в списке)

**Generate** → ждёшь 20-30 секунд → панель появляется в холсте Krita.

## Шаг 10: character-pipeline (опционально, 15 мин)

Для серии с одним лицом в разных сценах — IP-Adapter workflow. Скачать референс (одна панель лица) → положить в `app/input/jill-face-ref.png` → отправить workflow из `character-series-prompts.json`.

Или запустить напрямую через ComfyUI API (без Krita):
```bash
curl -X POST --noproxy 127.0.0.1,localhost \
  -H "Content-Type: application/json" \
  --data-binary @workflow.json \
  http://127.0.0.1:8188/prompt
```

Время на 6 панелей: ~15-20 мин.

## Шаг 11: проверить всё работает

Чек-лист:
- [ ] ComfyUI отвечает на `curl http://127.0.0.1:8188/system_stats`
- [ ] `curl http://127.0.0.1:8188/api/etn/model_info/checkpoints` возвращает 5 чекпойнтов
- [ ] Krita → Настройка → Панели → AI Image Generation (docker есть)
- [ ] В docker'е кружок зелёный
- [ ] Generate тестового промпта даёт панель за 30 сек
- [ ] IP-Adapter workflow создаёт 6 панелей с одним лицом

Если что-то не так — открой `client.log` плагина (`%APPDATA%/krita/ai_diffusion/logs/client.log`) и `comfyui-run.log`. В них будет причина.

## Когда что использовать (agent cheatsheet)

| Задача | Модель | Скорость | Когда НЕ использовать |
|---|---|---|---|
| Аниме, манга, VA-11 HALL-A | Nova Anime XL | 18-20 сек | фотореал, текст в кадре |
| Фотореал портрет | RealVisXL v5.0 | 23 сек | аниме (будет «как фото аниме-девушки») |
| Постер, sci-fi, CGI | JuggernautXL v9 | 27 сек | аниме (будет «слишком кинематографично») |
| Фэнтези, концепт-арт | DreamShaperXL Turbo | 30 сек | быстрые тесты (медленно) |
| Baseline / fallback | SDXL base 1.0 | 20 сек | для стилизованного арта (будет нейтрально) |
| Серия с одним лицом | Nova Anime XL + IP-Adapter | 2-3 мин/панель | единичный кадр (overkill) |
| Лучшая идентичность в серии | LLaDA-Image-Turbo (editing) | 21 мин/панель | быстрые драфты |
| Сложный одиночный, текст в кадре | Gemini 3.1 (облако) | 8-12 сек, $0.034 | серия (лицо плывёт) |

## Что может пойти не так

- **Krita 6 установлена, плагин не виден** — скачать Krita 5.2.11, откатить версию.
- **`server_mode: 1` в settings.json** — заменить на `"external"` (строка).
- **`tensor a (4) must match tensor b (128)`** — VAE не тот, нужен SDXL VAE.
- **`Missing required node InpaintPreprocessor`** — `comfyui_controlnet_aux` не клонирован.
- **`Missing required node IPAdapterModelLoader`** — `ComfyUI_IPAdapter_plus` не клонирован.
- **`Missing common models: OmniSR/MAT`** — не скачаны `models/upscale_models/OmniSR_*.safetensors` и `models/inpaint/MAT_*.safetensors`.
- **`clip input is invalid`** — чекпойнт не содержит CLIP, скачивать полный safetensors из корня HF репо.
- **curl качает 29-байтный pointer** — корпоративный прокси, использовать `python urllib` с `User-Agent: Mozilla/5.0`.
- **IP-Adapter не работает** — в новой `ComfyUI_IPAdapter_plus` нода называется `IPAdapter` (не `IPAdapterApply`), `weight_type` принимает только `standard | prompt is more important | style transfer`, `clip_vision` подавать явно через `IPAdapterAdvanced`.
- **docker не виден в Krita** — плагин не через `Tools → Scripts → Import`, а скопирован вручную. Переустановить через UI + рестарт.

## Скрипт автозагрузки моделей

См. файл `download-bonus4-bundle.py` в этом же репо. Запускается один раз, скачивает 15 файлов в правильные папки. Поддерживает resume (если оборвалось — перезапустить, докачает).

## Итоговый результат

После всех шагов:
- Локальный арт-стек, 0 руб/кадр, 20-30 сек/панель
- 5 стилей на выбор (аниме/фото/постер/фэнтези/нейтральный)
- Серия с одним лицом через IP-Adapter
- Inpaint через Krita (выделение → промпт → перерисовка)
- Upscale 4× через Krita
- 100% offline (после скачивания моделей)
