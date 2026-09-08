import os
import sys
import json
import time
import base64
import io
import subprocess
import requests
import runpod

# ============ KONFIGURASI ============
COMFYUI_DIR = os.getenv("COMFYUI_DIR", "/comfyui")
COMFYUI_PORT = int(os.getenv("COMFYUI_PORT", "8188"))
COMFYUI_URL = f"http://127.0.0.1:{COMFYUI_PORT}"
WORKFLOW_PATH = os.getenv("WORKFLOW_PATH", "/app/workflow_api.json")
WORKFLOW_UI_PATH = os.getenv("WORKFLOW_UI_PATH", "/app/workflow_ui.json")
NODE_MAP_PATH = os.getenv("NODE_MAP_PATH", "/app/node_map.json")
OUTPUT_DIR = os.path.join(COMFYUI_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

comfyui_process = None
node_map_cache = None


def ensure_comfyui():
    global comfyui_process

    if comfyui_process is not None and comfyui_process.poll() is None:
        return

    print("Starting ComfyUI...")
    env = os.environ.copy()
    env["PYTHONPATH"] = COMFYUI_DIR

    comfyui_process = subprocess.Popen(
        [
            sys.executable,
            os.path.join(COMFYUI_DIR, "main.py"),
            "--listen", "127.0.0.1",
            "--port", str(COMFYUI_PORT),
            "--preview-method", "none",
            "--disable-auto-launch",
        ],
        cwd=COMFYUI_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    for _ in range(600):
        if comfyui_process.poll() is not None:
            out = ""
            if comfyui_process.stdout:
                out = comfyui_process.stdout.read()
            raise RuntimeError(f"ComfyUI exited:\n{out[-3000:]}")

        try:
            r = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
            if r.status_code == 200:
                print("ComfyUI ready")
                return
        except Exception:
            time.sleep(2)

    raise TimeoutError("ComfyUI tidak siap setelah 20 menit")


def ensure_workflow_api():
    if os.path.exists(WORKFLOW_PATH):
        return

    print("workflow_api.json belum ada, generate otomatis...")

    if not os.path.exists(WORKFLOW_UI_PATH):
        print("Download workflow UI...")
        import workflow_downloader
        workflow_downloader.main()

    import workflow_converter
    workflow_converter.save_api(WORKFLOW_UI_PATH, WORKFLOW_PATH, COMFYUI_URL)


def load_node_map():
    global node_map_cache
    if node_map_cache is None:
        if os.path.exists(NODE_MAP_PATH):
            with open(NODE_MAP_PATH, "r") as f:
                node_map_cache = json.load(f)
        else:
            node_map_cache = {}
    return node_map_cache


def find_nodes_by_class(wf, classes):
    ids = []
    for nid, node in wf.items():
        if node.get("class_type") in classes:
            ids.append(nid)
    return ids


def find_nodes_by_title(wf, phrases):
    ids = []
    for nid, node in wf.items():
        title = node.get("_meta", {}).get("title", "")
        if any(p.lower() in title.lower() for p in phrases):
            ids.append(nid)
    return ids


def to_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def upload_image(image_b64, name_hint="input.png"):
    img_bytes = base64.b64decode(image_b64)
    files = {"image": (name_hint, io.BytesIO(img_bytes), "image/png")}
    r = requests.post(f"{COMFYUI_URL}/upload/image", files=files, timeout=30)
    r.raise_for_status()
    return r.json()["name"]


def load_workflow():
    with open(WORKFLOW_PATH, "r") as f:
        return json.load(f)


def resolve_loras(job):
    raw = job.get("loras", {})

    if isinstance(raw, list):
        high, low = [], []
        for item in raw:
            if isinstance(item, str):
                name, strength = item, 0.85
            else:
                name = item.get("name") or item.get("file")
                strength = item.get("strength", 0.85)

            if name.endswith("_HIGH"):
                high.append({"name": name, "strength": strength})
            elif name.endswith("_LOW"):
                low.append({"name": name, "strength": strength})
            else:
                high.append({"name": name, "strength": strength})
        return high, low

    return raw.get("high", []), raw.get("low", [])


def set_lora_inputs(node, lora):
    inp = node["inputs"]
    inp["lora_name"] = lora.get("name") or lora.get("file")

    if "strength_model" in inp:
        inp["strength_model"] = lora.get("strength", 0.85)
    if "strength_clip" in inp:
        inp["strength_clip"] = lora.get("strength_clip", lora.get("strength", 0.85))


def mutate_workflow(wf, job, image_name):
    node_map = load_node_map()

    # 1. Load image
    image_ids = to_list(node_map.get("load_image")) or find_nodes_by_class(
        wf, ["LoadImage", "LoadImageMask"]
    )
    for nid in image_ids:
        if nid in wf:
            wf[nid]["inputs"]["image"] = image_name

    prompt = job.get("prompt", "")
    negative_prompt = job.get("negative_prompt", "bad quality, blurry, deformed")

    # 2. Positive prompt
    pos_ids = to_list(node_map.get("positive_prompt")) or find_nodes_by_title(
        wf, ["positive", "pos prompt"]
    )
    if not pos_ids:
        pos_ids = find_nodes_by_class(wf, ["CLIPTextEncode"])
    for nid in pos_ids:
        if nid in wf:
            wf[nid]["inputs"]["text"] = prompt

    # 3. Negative prompt
    neg_ids = to_list(node_map.get("negative_prompt")) or find_nodes_by_title(
        wf, ["negative", "neg prompt"]
    )
    if len(neg_ids) >= 2:
        neg_ids = neg_ids[1:]
    for nid in neg_ids:
        if nid in wf:
            wf[nid]["inputs"]["text"] = negative_prompt

    # 4. Latent / resolusi / durasi
    width = int(job.get("width", 768))
    height = int(job.get("height", 1280))
    num_frames = int(job.get("num_frames", 81))

    latent_ids = to_list(node_map.get("latent")) or find_nodes_by_class(
        wf,
        [
            "EmptyHunyuanLatentVideo",
            "EmptyLatentVideo",
            "EmptyLatentImage",
            "EmptySD3LatentImage",
        ],
    )
    for nid in latent_ids:
        if nid not in wf:
            continue
        inp = wf[nid]["inputs"]
        if "width" in inp:
            inp["width"] = width
        if "height" in inp:
            inp["height"] = height
        if "length" in inp:
            inp["length"] = num_frames
        elif "batch_size" in inp:
            inp["batch_size"] = num_frames

    # 5. Steps / CFG / seed
    steps = int(job.get("steps", 8))
    cfg = float(job.get("cfg", 1.5))
    seed = int(job.get("seed", 0))

    for nid, node in wf.items():
        class_type = node.get("class_type")
        inp = node.get("inputs", {})

        if class_type == "KSampler":
            if "steps" in inp:
                inp["steps"] = steps
            if "cfg" in inp:
                inp["cfg"] = cfg
            if "seed" in inp:
                inp["seed"] = seed

        if class_type == "SamplerCustomAdvanced":
            if "noise_seed" in inp:
                inp["noise_seed"] = seed

        if class_type == "BasicScheduler":
            if "steps" in inp:
                inp["steps"] = steps

    # 6. LoRA high/low
    high_loras, low_loras = resolve_loras(job)
    all_lora_nodes = find_nodes_by_class(wf, ["LoraLoader", "LoraLoaderModelOnly"])

    map_high = to_list(node_map.get("lora_high"))
    map_low = to_list(node_map.get("lora_low"))

    if not map_high and not map_low and all_lora_nodes:
        map_high = find_nodes_by_title(wf, ["high"])
        map_low = find_nodes_by_title(wf, ["low"])

        used = set(map_high) | set(map_low)
        remaining = [nid for nid in all_lora_nodes if nid not in used]

        if not map_high and not map_low:
            map_high = remaining[: len(high_loras)]
            map_low = remaining[len(high_loras): len(high_loras) + len(low_loras)]

    for i, nid in enumerate(map_high):
        if nid in wf and i < len(high_loras):
            set_lora_inputs(wf[nid], high_loras[i])

    for i, nid in enumerate(map_low):
        if nid in wf and i < len(low_loras):
            set_lora_inputs(wf[nid], low_loras[i])

    # 7. Audio prompt MMAudio
    audio_prompt = job.get("audio_prompt")
    if audio_prompt:
        audio_ids = to_list(node_map.get("audio_prompt")) or find_nodes_by_title(
            wf, ["audio", "mmaudio", "sound"]
        )
        for nid in audio_ids:
            if nid in wf:
                wf[nid]["inputs"]["prompt"] = audio_prompt


def wait_for_completion(prompt_id, timeout=1800):
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(5)
        try:
            r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
            r.raise_for_status()
            history = r.json()
        except Exception:
            continue

        if prompt_id in history:
            item = history[prompt_id]
            status = item.get("status", {})
            outputs = item.get("outputs", {})

            if outputs or status.get("completed"):
                return item
            if status.get("status_str") == "error" or "error" in item:
                raise RuntimeError(f"ComfyUI error: {json.dumps(item)[:3000]}")

    raise TimeoutError("Generate video timeout")


def find_video_output(history_item):
    for node_id, out in history_item.get("outputs", {}).items():
        for key in ("gifs", "videos", "animated"):
            if key in out:
                for file_info in out[key]:
                    return (
                        file_info.get("filename"),
                        file_info.get("subfolder", ""),
                        file_info.get("type", "output"),
                    )
    return None


def base64_file(filename, subfolder, type_):
    if not filename:
        return None

    path = os.path.join(OUTPUT_DIR, subfolder, filename)
    if not os.path.exists(path):
        path = os.path.join(OUTPUT_DIR, filename)

    if not os.path.exists(path):
        return None

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def handler(job):
    ensure_comfyui()
    ensure_workflow_api()

    inp = job.get("input", {})
    image_b64 = inp.get("image_b64") or inp.get("image")
    image_url = inp.get("image_url")

    if image_url and not image_b64:
        print(f"Downloading image from URL: {image_url[:80]}")
        r_img = requests.get(image_url, timeout=30)
        r_img.raise_for_status()
        image_b64 = base64.b64encode(r_img.content).decode()

    if not image_b64:
        return {"status": "error", "error": "image_b64 atau image_url wajib diisi"}

    uploaded_name = upload_image(image_b64)

    wf = load_workflow()
    mutate_workflow(wf, inp, uploaded_name)

    r = requests.post(
        f"{COMFYUI_URL}/prompt",
        json={"prompt": wf},
        timeout=30,
    )
    r.raise_for_status()
    prompt_id = r.json()["prompt_id"]

    history_item = wait_for_completion(prompt_id)

    out = find_video_output(history_item)
    if not out:
        return {
            "status": "error",
            "error": "Output video tidak ditemukan",
            "history": history_item,
        }

    filename, subfolder, type_ = out
    video_b64 = base64_file(filename, subfolder, type_)

    if not video_b64:
        return {
            "status": "error",
            "error": "File output tidak ada di disk",
            "file": out,
        }

    return {
        "status": "success",
        "prompt_id": prompt_id,
        "filename": filename,
        "mime": "video/mp4" if filename.endswith(".mp4") else "video/webm",
        "video_b64": video_b64,
    }


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
