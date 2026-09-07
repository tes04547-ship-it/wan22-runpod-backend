#!/bin/bash
set -e

cd /workspace/backend

pip install -q huggingface_hub hf_transfer tqdm requests

export CIVITAI_API_KEY="52c29ab2bbe8836d62e6bb9d03ef3338"
export MODELS_DIR="/workspace/ComfyUI/models"
export LORAS_JSON="/workspace/backend/loras.json"

python download_models.py
