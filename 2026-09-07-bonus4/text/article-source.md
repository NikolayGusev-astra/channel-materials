# Бонус 4: Локальный арт за 0 рублей — 5 стилей и серия с одним лицом

В Бонусах 1-3 я показывал облачные модели (Gemini 3.1 flash-lite-image за $0.034/кадр, LLaDA-Image-Turbo через ComfyUI). В Бонусе 4 — полностью локальный конвейер: 5 чекпойнтов SDXL на 8 ГБ VRAM, 0 рублей за кадр, 20-30 секунд на панель 1024×1024. Плюс пайплайн «один персонаж в 6 сценах» с IP-Adapter — одно лицо узнаётся между кадрами, одежда и поза меняются.

## Зачем

Подписки на Midjourney / Adobe Firefly / DALL-E — это $10-30/месяц и привязка к облаку. Локальный стек: 40 ГБ моделей скачиваются один раз, дальше рисуешь сколько влезет. Для аниме-комиксов Nova Anime XL не уступает Gemini по качеству, для фотореала RealVisXL, для постеров JuggernautXL. Всё на своём железе, без интернета после скачивания.

## Стек за 1 минуту

Софт (всё портативное, без установки):

- **Krita 5.2.11** — портативный графический редактор. Не 6.x — плагин AI Diffusion v1.53.0 не работает на Krita 6.
- **AI Diffusion v1.53.0** — плагин Krita, рисует в холсте через наш же ComfyUI. Импортируется через `Tools → Scripts → Import Python Plugin from File…` (не копировать вручную).
- **ComfyUI 0.34** — наш, тот же что для LLaDA. Слушает :8188.
- **ImageMagick 7.1.2-31 portable** — для инфографики и склейки стрипов.
- **Python 3.11 venv** — для автоматизации и скриптов.

Модели (всё в `models/` ComfyUI):

- **5 SDXL-чекпойнтов** в `checkpoints/`: Nova Anime XL 7.1 ГБ (аниме), RealVisXL v5.0 6.9 ГБ (фотореал), JuggernautXL v9 7.1 ГБ (постер/CGI), DreamShaperXL Turbo 6.9 ГБ (фэнтези), SDXL base 1.0 6.9 ГБ (нейтральный baseline).
- **Hyper-SDXL-8steps lora** 0.8 ГБ в `loras/` — 8 шагов вместо 30, без потери качества.
- **SDXL VAE** 0.3 ГБ в `vae/` — обязательно, не перепутать с FLUX-VAE (тот вызовет ошибку `tensor a (4) must match tensor b (128)`).
- **SDXL text encoders** 0.5+2.8 ГБ в `text_encoders/` — clip_l + clip_g для unet-only чекпойнтов.
- **IP-Adapter SDXL** 0.7 ГБ в `ipadapter/` + **CLIP-Vision** 2.5 ГБ в `clip_vision/` — для сохранения лица персонажа в серии.
- **Fooocus inpaint** 1.3 ГБ в `inpaint/` — для правки отдельных областей.
- **4x NMKD Superscale** 67 МБ + **OmniSR X2/X3/X4** 5 МБ в `upscale_models/` — апскейлеры.
- **MAT inpaint** 125 МБ в `inpaint/` — требуется плагином Krita как «required common model».

Итого: ~40 ГБ локальных моделей. Скачиваются один раз, дальше бесплатно.

Все чекпойнты скачиваются с Hugging Face. Скрипт автозагрузки лежит в материалах к статье (см. раздел «Установка» в конце).

## Скорость и стоимость

1024×1024, 8 шагов, CFG 2.0, euler/normal, Hyper-SDXL lora strength 0.9 — универсальные настройки для всех моделей.

| Модель | Секунд/кадр (8 ГБ VRAM) | Стиль | Цена за 1000 кадров |
|---|---|---|---|
| Nova Anime XL | 18-20 | аниме | 0 руб |
| RealVisXL v5.0 | 23 | фотореал | 0 руб |
| JuggernautXL v9 | 27 | постер, CGI | 0 руб |
| DreamShaperXL Turbo | 30 | фэнтези | 0 руб |
| SDXL base 1.0 | 20 | нейтральный | 0 руб |
| **Gemini 3.1 flash-lite-image** (для сравнения) | 8-12 | любой | **$34** |

Локальные модели медленнее в 2-3 раза, но бесплатные. За 1000 кадров экономия $34, за 10000 — $340.

## Тест: один персонаж в 5 стилях

Один и тот же промпт-каркас «young woman bartender, purple hair in two round buns, white shirt, black vest, tired kind eyes» — прогон через 5 разных моделей. Стилевые модификаторы в промпте меняются, негатив общий.

Nova Anime XL (аниме): `1girl, solo, ..., anime coloring, masterpiece, best quality, detailed background`

RealVisXL (фотореал): `RAW photo, 8k uhd, dslr, soft lighting, Canon EOS R5, 35mm lens f/1.8, bokeh, photorealistic, hyperdetailed, ...`

JuggernautXL (постер): `cinematic still, dramatic lighting, hollywood cinematography, anamorphic lens, depth of field, color grading, 8k, masterpiece, ...`

DreamShaperXL (художественный): `digital painting, concept art, trending on artstation, art by greg rutkowski, fantasy, intricate detail, ...`

SDXL base (нейтральный): без стилевых модификаторов.

Негатив общий: `lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, worst quality, low quality, blurry, watermark`.

Результат — пять панелей, по одной от каждой модели. Слева направо: Nova Anime XL, RealVisXL, JuggernautXL, DreamShaperXL, SDXL base.

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-styles/style-test-5panels.png]

Каждая модель даёт свой визуальный мир для одного и того же персонажа. Nova Anime XL — узнаваемо аниме, RealVisXL — фотореалистичный портрет, JuggernautXL — кинематографичный постер, DreamShaperXL — картина маслом, SDXL base — нейтральная baseline.

Если нужно кликнуть — откроется полный размер.

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-styles/01-nova-anime.png | Nova Anime XL — аниме-стиль Illustrious]

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-styles/02-realvis-photo.png | RealVisXL v5.0 — фотореал]

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-styles/03-juggernaut-poster.png | JuggernautXL v9 — кинематографичный постер]

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-styles/04-dreamshaper-fantasy.png | DreamShaperXL Turbo — фэнтези]

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-styles/05-sdxl-baseline.png | SDXL base 1.0 — нейтральный baseline]

## Character pipeline: один персонаж в 6 сценах

Главная проблема комиксов и серий: как сохранить одно лицо между панелями, если одежда, поза, фон и настроение меняются. Решение — IP-Adapter: он сохраняет визуальную идентичность через face-embedding, а сцену мы меняем через промпт.

### Как это работает

Стек IP-Adapter в ComfyUI (порядок нод):

1. `LoadImage` — загружаем референс лица (одна панель персонажа).
2. `CLIPVisionLoader` — кодировщик изображения (clip-vision_vit-h).
3. `IPAdapterModelLoader` — модель IP-Adapter (ip-adapter_sdxl_vit-h).
4. `IPAdapterAdvanced` — применяет face-embedding к модели, weight 0.75, embeds_scaling «V only».
5. `CheckpointLoaderSimple` (Nova Anime XL) + `LoraLoader` (Hyper-SDXL) — базовая модель.
6. `CLIPTextEncode` — промпт сцены (одежда, поза, настроение).
7. `KSampler` — sampler (euler, 8 steps, CFG 2.0).
8. `VAEDecode` → `SaveImage`.

Важно: в новой версии `ComfyUI_IPAdapter_plus` нода называется `IPAdapter` (не `IPAdapterApply`), параметр `weight_type` принимает только `standard | prompt is more important | style transfer` (не `linear`), и `clip_vision` нужно подавать явно через `IPAdapterAdvanced` (а не простой `IPAdapter`).

### Пример: 6 сцен Джилл Стингрей

Один и тот же референс лица + 6 разных промптов: пижама утром, на работу, за стойкой, грустная ночью, под дождём, спит на диване. Лицо одно, одежда/поза/свет разные.

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-character/character-series-strip.png | 6-панельная серия Джилл через IP-Adapter]

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-character/character-series-with-ref.png | Референс + 6 панелей — видно как лицо держится между кадрами]

Время на 6 панелей: ~15-20 минут на 8 ГБ VRAM (IP-Adapter + CLIP-Vision + Nova Anime XL).

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-character/01-pijamas.png | Утро в пижаме, кофе]

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-character/02-na-rabotu.png | На работу, идёт по улице]

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-character/03-za-stojkoy.png | За стойкой VA-11 HALL-A]

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-character/04-grustnaya.png | Ночью, грустная, облокотившись на стойку]

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-character/05-rain.png | Под дождём, бежит к двери]

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-character/06-spit.png | Дома в свитере, спит на диване]

## Сравнение с LLaDA и Gemini

Джилл Стингрей — та же самая серия, 3 разных модели, одинаковые промпты.

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-nova/compare-nova-llada-gemini.png | 3-way сравнение: Nova Anime XL (локально), LLaDA-Image-Turbo (локально), Gemini 3.1 (облако)]

[IMG: https://raw.githubusercontent.com/NikolayGusev-astra/channel-materials/master/2026-09-07-bonus4-nova/jill-nova-strip.png | 6 панелей Джилл через Nova Anime XL (локально)]

| Модель | Цена 6 панелей | Идентичность 6/6 | Скорость | Сильная сторона |
|---|---|---|---|---|
| LLaDA-Image-Turbo (локально) | 0 руб | лучшая | 21 мин/панель | editing, точно держит лицо через image-edit |
| Nova Anime XL (локально) | 0 руб | хорошая (IP-Adapter) | 4-5 мин/панель | баланс скорости и качества, t2i |
| Gemini 3.1 flash-lite-image (облако) | $0.20/6 панелей | плавает | 8-12 сек/панель | богатая детализация, фотореал |

Вывод для серий: LLaDA editing — лучшая идентичность, но медленно. Nova Anime XL + IP-Adapter — хорошая идентичность и в 4 раза быстрее. Gemini — быстро, но лицо «плывёт» между панелями.

## Когда что использовать

| Задача | Модель | Почему |
|---|---|---|
| Аниме-комикс, манга, VA-11 HALL-A | Nova Anime XL | обучен на Illustrious, лучший аниме-стиль |
| Фотореалистичный портрет, лайфстайл | RealVisXL v5.0 | детальные текстуры кожи, bokeh |
| Кинематографичный постер, sci-fi, CGI | JuggernautXL v9 | anamorphic lens, color grading |
| Фэнтези-иллюстрация, концепт-арт | DreamShaperXL Turbo | стиль art by greg rutkowski |
| Ничего не подошло — fallback | SDXL base 1.0 | нейтральный, официальный |
| Серия комикса (одно лицо в 6+ сценах) | Nova Anime XL + IP-Adapter | держит идентичность, быстро |
| Промпт-инжиниринг сцены → правка лица | LLaDA-Image-Turbo (editing) | лучшая идентичность через image-edit |
| Сложный единичный кадр, фотореал, текст в кадре | Gemini 3.1 (облако) | $0.034/кадр, 8 сек, но идентичность плавает |

## Установка

Все скрипты, конфиги, чекпойнты, иллюстрации в репозиториях:

- **GitHub**: github.com/NikolayGusev-astra/channel-materials (папка `2026-09-07-bonus4-`)
- **GitFlic** (зеркало): gitflic.ru/project/manve-sulimo2/channel-materials

Полный README с пошаговой установкой от 0 до первой панели лежит в `2026-09-07-bonus4/README-install.md`. Краткая выжимка:

1. Скачать Krita 5.2.11 portable (с `download.kde.org/Attic/krita/5.2.11/`).
2. Импортировать плагин AI Diffusion v1.53.0 через `Tools → Scripts → Import Python Plugin from File…`.
3. Установить кастом-ноды в ComfyUI: `comfyui_controlnet_aux`, `ComfyUI_IPAdapter_plus` (через `git clone` в `app/custom_nodes/`).
4. Поставить `opencv-python-headless` в venv (`pip install opencv-python-headless`).
5. Скачать 5 чекпойнтов SDXL, 2 text encoder, 1 SDXL VAE, 1 IP-Adapter, 1 CLIP-Vision, Hyper-SDXL lora, Fooocus inpaint, 4x NMKD upscaler, OmniSR X2/X3/X4, MAT inpaint. Скрипт автозагрузки в материалах.
6. Запустить ComfyUI с флагами `--lowvram --reserve-vram 0.5 --disable-auto-launch --listen 127.0.0.1 --port 8188`.
7. Запустить Krita, открыть документ, `Настройка → Панели → AI Image Generation` → Configure → Custom Server → `http://127.0.0.1:8188` → Connect.
8. Открыть промпт, нажать Generate. Первая панель через 20-30 секунд.

## Грабли (на что убил время)

- **Krita 6 не подходит**. Плагин v1.53.0 в `__init__.py` явно проверяет `KRITA_VERSION_MAJOR == 5`. Скачивать именно Krita 5.2.x.
- **Плагин импортировать через UI**, не копировать в `pykrita/` руками. Иначе `.desktop` зарегистрируется, но QDockWidget не появится в меню. После импорта — рестарт Krita обязателен.
- **`server_mode` — строка, не число**. В settings.json должно быть `"server_mode": "external"`, иначе плагин молча откатится на `undefined` и не подключится.
- **SDXL VAE обязателен**. `LLaDa_VAE.safetensors` — это FLUX (8x latent), Nova Anime XL — SDXL (4x). Несовместимо. Скачивать `sdxl_vae.safetensors` 334 МБ с `madebyollin/sdxl-vae-fp16-fix`.
- **Некоторые «SDXL-чекпойнты» в Hugging Face — это только UNet**. `Lykon/dreamshaper-xl-1-0/unet/diffusion_pytorch_model.fp16.safetensors` — без CLIP/VAE внутри, при загрузке через `CheckpointLoaderSimple` будет «clip input is invalid». Скачивать полный `*.safetensors` чекпойнт из корня репо, либо использовать `DualCLIPLoader` + внешний VAE.
- **MAT и OmniSR обязательны для плагина Krita**. Плагин считает их required common models, без них «Missing common models» блокирует подключение. Это 125 МБ + 5 МБ, не пропускать.
- **Hugging Face через корпоративный прокси** отдаёт LFS-pointer 29 байт вместо файла. Решение: `python urllib` с `User-Agent: Mozilla/5.0` (curl пробивает хуже). Скрипт `download-xl-bundle.py` в материалах делает это правильно.
- **IP-Adapter в новой версии `ComfyUI_IPAdapter_plus`**: нода называется `IPAdapter` (не `IPAdapterApply`), `weight_type` принимает только `standard | prompt is more important | style transfer` (не `linear`), `clip_vision` нужно подавать явно через `IPAdapterAdvanced`.

## Что в материалах

Все промпты, чекпойнты, конфиги, иллюстрации в одной папке `2026-09-07-bonus4/` репозитория:

- `README-install.md` — пошаговая установка от 0 до первой панели для агента
- `download-bonus4-bundle.py` — скрипт автозагрузки 17 моделей с HF через `python urllib` (обходит прокси-баг curl)
- `text/article-source.md` — исходник этой статьи
- `prompts/` — JSON с промптами для воспроизведения
- `styles/` — 5 панелей «один персонаж в 5 стилях» + лист сравнения
- `character/` — 6-панельная серия «Джилл в 6 сценах» через IP-Adapter + лист + референс
- `nova/` — 6-панельный стрип Джилл через Nova + 3-way сравнение с LLaDA и Gemini

Telegraph-статья ссылается на эти файлы через raw-ссылки GitHub (или GitFlic зеркало). Имена файлов стабильные — можно ссылаться в новых статьях.

## Что в следующей статье

Эта статья — про 5 стилей и серию с одним лицом. Следующая — **«Бонус 5: позы, inpaint и дорисовка деталей»**: ControlNet OpenPose (точная поза по скелету), inpaint в Krita (выделение → перерисовка только части), SDXL ControlNet inpaint (правка рук, лица, фона без перегенерации). Следите за обновлениями.
