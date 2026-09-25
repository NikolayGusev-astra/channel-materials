import json
import os
import urllib.request

for key in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'):
    os.environ.pop(key, None)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = 'http://127.0.0.1:8188'
CORE = 'young woman bartender, purple hair in two round buns, white shirt, black vest, black tie, rolled sleeves, black skirt, tired kind eyes'

SCENES = [
    (
        'cover',
        f'{CORE}, standing behind a late-night bar counter and inspecting a floating wall of nine compact glowing model containers, a small brass balance scale and a magnifying glass beside her, warehouse shelves of quantization boxes behind the bar, two containers bright blue and two warm amber, focused skeptical expression, cinematic dark blue and violet lighting with warm bar lamp, polished anime editorial illustration, no text, no letters, no logos, no watermark',
    ),
    (
        'downloads-vs-quality',
        f'{CORE}, acting as a strict engineer at a test bench, looking at two large mechanical gauges: one crowded with many small blue download icons and another mostly empty with a small unfinished checklist, holding a caliper over a GGUF model block, cautious expression, dark technical laboratory, cinematic indigo and orange lighting, polished anime editorial illustration, no text, no letters, no logos, no watermark',
    ),
    (
        'specialists',
        f'{CORE}, standing between three workstations: a large scanned document page under a magnifier, a terminal with abstract green code lines, and a tiny router choosing one highlighted option from many dim buttons, tired capable expression, clean dark workspace, blue violet and orange accent lighting, polished anime editorial illustration, no readable text, no letters, no logos, no watermark',
    ),
]


def build(name, scene):
    return {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'qwen_image_2.1_int8_convrot.safetensors', 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': 'qwen3vl_8b_w4a8.safetensors', 'type': 'qwen_image', 'device': 'default'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'qwen_image_2.1_vae_bf16.safetensors'}},
        '9': {'class_type': 'LoadImage', 'inputs': {'image': 'ref_canon.png'}},
        '4': {'class_type': 'TextEncodeQwenImage21', 'inputs': {
            'clip': ['2', 0], 'prompt': scene, 'negative_prompt': 'bad anatomy, bad hands, extra fingers, duplicate limbs, deformed face, text, letters, words, logo, watermark',
            'resolution': 1024, 'images.image_1': ['9', 0], 'vae': ['3', 0],
        }},
        '6': {'class_type': 'KSampler', 'inputs': {
            'model': ['1', 0], 'positive': ['4', 0], 'negative': ['4', 1], 'latent_image': ['4', 2],
            'seed': 250925 + len(name), 'steps': 25, 'cfg': 1.0, 'sampler_name': 'euler',
            'scheduler': 'simple', 'denoise': 1.0,
        }},
        '7': {'class_type': 'VAEDecode', 'inputs': {'samples': ['6', 0], 'vae': ['3', 0]}},
        '8': {'class_type': 'SaveImage', 'inputs': {'images': ['7', 0], 'filename_prefix': f'bartowski-week/{name}'}},
    }


queue = json.load(opener.open(BASE + '/queue', timeout=10))
if queue.get('queue_running') or queue.get('queue_pending'):
    raise SystemExit('QUEUE BUSY')

for name, scene in SCENES:
    payload = json.dumps({'prompt': build(name, scene), 'client_id': 'rin-bartowski-week'}).encode()
    req = urllib.request.Request(BASE + '/prompt', data=payload, headers={'Content-Type': 'application/json'})
    result = json.load(opener.open(req, timeout=60))
    print(name, result['prompt_id'], flush=True)
