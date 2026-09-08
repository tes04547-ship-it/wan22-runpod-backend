FROM runpod/base:0.4.0-cuda12.1.0

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/runpod-volume/hf_cache \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    COMFYUI_DIR=/app/ComfyUI \
    COMFYUI_PORT=8188 \
    MODELS_DIR=/runpod-volume/ComfyUI/models

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git git-lfs aria2 wget curl ca-certificates unzip \
        ffmpeg libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
        build-essential python3 python3-pip python3-dev && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip

# ============ COMFYUI (clone dulu, lalu install req) ============
RUN git clone https://github.com/comfyanonymous/ComfyUI.git ${COMFYUI_DIR} && \
    cd ${COMFYUI_DIR} && \
    pip install --no-cache-dir -r requirements.txt

# ============ FIX: Install missing deps ============
RUN pip install --no-cache-dir \
    sqlalchemy aiosqlite aiohttp alembic blake3 comfy_kitchen nvidia-ml-py \
    einops einops-exts ftfy regex safetensors sentencepiece protobuf \
    accelerate transformers diffusers av opencv-python-headless \
    librosa soundfile psutil omegaconf timm pydantic python-dotenv \
    || true

# ============ CUSTOM NODES (tahan gagal) ============
RUN mkdir -p ${COMFYUI_DIR}/custom_nodes && cd ${COMFYUI_DIR}/custom_nodes && \
    (git clone --depth=1 https://github.com/kijai/ComfyUI-WanVideoWrapper.git || echo "FAILED: WanVideoWrapper") && \
    (git clone --depth=1 https://github.com/city96/ComfyUI-GGUF.git || echo "FAILED: GGUF") && \
    (git clone --depth=1 https://github.com/kijai/ComfyUI-KJNodes.git || echo "FAILED: KJNodes") && \
    (git clone --depth=1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git || echo "FAILED: VideoHelperSuite") && \
    (git clone --depth=1 https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git || echo "FAILED: Frame-Interpolation") && \
    (git clone --depth=1 https://github.com/kijai/ComfyUI-MMAudio.git || echo "FAILED: MMaAudio") && \
    (git clone --depth=1 https://github.com/sipherxyz/comfyui-art-venture.git || echo "FAILED: art-venture") && \
    (git clone --depth=1 https://github.com/cubiq/ComfyUI_essentials.git || echo "FAILED: essentials") && \
    (git clone --depth=1 https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet.git || echo "FAILED: Advanced-ControlNet") && \
    (git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Impact-Pack.git || echo "FAILED: Impact-Pack") && \
    (git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Manager.git || echo "FAILED: Manager") && \
    (git clone --depth=1 https://github.com/jags111/efficiency-nodes-comfyui.git || echo "FAILED: efficiency") && \
    (git clone --depth=1 https://github.com/rgthree/rgthree-comfy.git || echo "FAILED: rgthree") && \
    (git clone --depth=1 https://github.com/crystian/ComfyUI-Crystools.git || echo "FAILED: Crystools") && \
    (git clone --depth=1 https://github.com/Jordach/comfy-plasma.git || echo "FAILED: comfy-plasma")

# Install requirements custom nodes
RUN cd ${COMFYUI_DIR}/custom_nodes && \
    for d in */; do \
      if [ -f "$d/requirements.txt" ]; then \
        pip install --no-cache-dir -r "$d/requirements.txt" || echo "skip $d"; \
      fi; \
    done

# ============ PIN TORCH 2.7.1 + CU118 (solusi utama) ============
RUN pip install --no-cache-dir --force-reinstall \
    torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 \
    --index-url https://download.pytorch.org/whl/cu118

# ============ MODEL PATH → NETWORK VOLUME ============
RUN mkdir -p /runpod-volume/ComfyUI/models && \
    rm -rf ${COMFYUI_DIR}/models && \
    ln -s /runpod-volume/ComfyUI/models ${COMFYUI_DIR}/models

# ============ BACKEND APP ============
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt || true

COPY handler.py /app/handler.py
COPY workflow_downloader.py /app/workflow_downloader.py
COPY workflow_converter.py /app/workflow_converter.py
COPY download_models.py /app/download_models.py
COPY loras.json /app/loras.json
COPY node_map.json /app/node_map.json
COPY inspect_workflow.py /app/inspect_workflow.py

# ============ NONAKTIFKAN ENTRYPOINT BAWAAN ============
ENTRYPOINT []

WORKDIR /app
CMD ["python3", "-u", "handler.py"]
