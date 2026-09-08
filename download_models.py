import os
import json
import requests
from tqdm.auto import tqdm
from huggingface_hub import hf_hub_download, hf_hub_url

BASE_MODEL_DIR = os.getenv("MODELS_DIR", "/runpod-volume/ComfyUI/models")
HF_TOKEN = os.getenv("HF_TOKEN", "")
CIVITAI_API_KEY = os.getenv("CIVITAI_API_KEY", "")
LORAS_JSON = os.getenv("LORAS_JSON", "/app/loras.json")

HF_BASE_DOWNLOADS = {
    "diffusion_models/wan2.2_i2v_high_noise_14B_Q4_K_S.gguf": (
        "bullerwins/Wan2.2-I2V-A14B-GGUF",
        "wan2.2_i2v_high_noise_14B_Q4_K_S.gguf",
    ),
    "diffusion_models/wan2.2_i2v_low_noise_14B_Q4_K_S.gguf": (
        "bullerwins/Wan2.2-I2V-A14B-GGUF",
        "wan2.2_i2v_low_noise_14B_Q4_K_S.gguf",
    ),
    "text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors": (
        "Comfy-Org/Wan_2.1_ComfyUI_repackaged",
        "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
    ),
    "vae/wan_2.1_vae.safetensors": (
        "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
        "split_files/vae/wan_2.1_vae.safetensors",
    ),
    "clip_vision/clip_vision_h.safetensors": (
        "Comfy-Org/Wan_2.1_ComfyUI_repackaged",
        "split_files/clip_vision/clip_vision_h.safetensors",
    ),
    "upscale_models/2xLexicaRRDBNet_Sharp.pth": (
        "Thelocallab/2xLexicaRRDBNet_Sharp",
        "2xLexicaRRDBNet_Sharp.pth",
    ),
}

HF_LORAS = {
    "loras/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors": (
        "Kijai/WanVideo_comfy",
        "LoRAs/Stable-Video-Infinity/v2.0/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors",
    ),
    "loras/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors": (
        "Kijai/WanVideo_comfy",
        "LoRAs/Stable-Video-Infinity/v2.0/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors",
    ),
    "loras/Wan2.2-Lightning_I2V-A14B-4steps-lora_HIGH_fp16.safetensors": (
        "Kijai/WanVideo_comfy",
        "LoRAs/Wan22-Lightning/old/Wan2.2-Lightning_I2V-A14B-4steps-lora_HIGH_fp16.safetensors",
    ),
    "loras/Wan2.2-Lightning_I2V-A14B-4steps-lora_LOW_fp16.safetensors": (
        "Kijai/WanVideo_comfy",
        "LoRAs/Wan22-Lightning/old/Wan2.2-Lightning_I2V-A14B-4steps-lora_LOW_fp16.safetensors",
    ),
}

MMAudio_DOWNLOADS = {
    "mmaudio/mmaudio_large_44k_v2.pth": ("hkchengrex/MMAudio", "weights/mmaudio_large_44k_v2.pth"),
    "mmaudio/best_netG.pt": ("hkchengrex/MMAudio", "ext_weights/best_netG.pt"),
    "mmaudio/synchformer_state_dict.pth": ("hkchengrex/MMAudio", "ext_weights/synchformer_state_dict.pth"),
    "mmaudio/encodec_24khz-d7cc33bc.th": ("dl.fbaipublicfiles.com", "encodec/v0/encodec_24khz-d7cc33bc.th"),
}

def download_hf_file(repo_id, filename, rel_dest):
    dest = os.path.join(BASE_MODEL_DIR, rel_dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
        print(f"SKIP {rel_dest}")
        return True

    print(f"DOWNLOAD {repo_id} / {filename}")
    try:
        local = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=BASE_MODEL_DIR,
            token=HF_TOKEN or None,
        )
        if local != dest and os.path.exists(local):
            os.replace(local, dest)
        if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
            print(f"OK {rel_dest}")
            return True
    except Exception as e:
        print(f"hf_hub_download gagal: {str(e)[:100]}")

    url = hf_hub_url(repo_id, filename)
    headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    with requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=300) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest + ".tmp", "wb") as f, tqdm(total=total, unit="B", unit_scale=True) as pbar:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                pbar.update(len(chunk))
    os.replace(dest + ".tmp", dest)
    print(f"OK {rel_dest}")
    return True

def download_civitai(version_id, filename):
    if not version_id:
        print(f"SKIP {filename}: version_id kosong")
        return False
    dest_dir = os.path.join(BASE_MODEL_DIR, "loras")
    dest = os.path.join(dest_dir, filename)
    os.makedirs(dest_dir, exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
        print(f"SKIP {filename}")
        return True

    headers = {"Authorization": f"Bearer {CIVITAI_API_KEY}"} if CIVITAI_API_KEY else {}
    url = f"https://civitai.com/api/download/models/{version_id}"
    print(f"DOWNLOAD CivitAI {filename} (version_id={version_id})")
    try:
        with requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=300) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            with open(dest + ".tmp", "wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=filename) as pbar:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
                    pbar.update(len(chunk))
        os.replace(dest + ".tmp", dest)
        print(f"OK {filename}")
        return True
    except Exception as e:
        print(f"GAGAL {filename}: {str(e)[:100]}")
        if os.path.exists(dest + ".tmp"):
            os.remove(dest + ".tmp")
        return False

def main():
    with open(LORAS_JSON, "r") as f:
        config = json.load(f)
    print("=" * 60)
    print("[1/4] Base + upscale")
    for rel, (repo, filename) in HF_BASE_DOWNLOADS.items():
        download_hf_file(repo, filename, rel)
    print("[2/4] SVI + LightX2V")
    for rel, (repo, filename) in HF_LORAS.items():
        download_hf_file(repo, filename, rel)
    print("[3/4] NSFW LoRA")
    for item in config["actions"]:
        download_civitai(item.get("version_id"), item.get("file"))
    print("[4/4] MMaAudio")
    for rel, (repo, filename) in MMAudio_DOWNLOADS.items():
        if repo == "dl.fbaipublicfiles.com":
            dest = os.path.join(BASE_MODEL_DIR, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
                print(f"SKIP {rel}")
                continue
            url = f"https://{repo}/{filename}"
            with requests.get(url, stream=True, allow_redirects=True, timeout=300) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                with open(dest + ".tmp", "wb") as f, tqdm(total=total, unit="B", unit_scale=True) as pbar:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        f.write(chunk)
                        pbar.update(len(chunk))
            os.replace(dest + ".tmp", dest)
            print(f"OK {rel}")
        else:
            download_hf_file(repo, filename, rel)
    print("Selesai")

if __name__ == "__main__":
    main()
