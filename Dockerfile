FROM runpod/base:0.4.0-cuda12.1.0

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    COMFYUI_DIR=/comfyui \
    COMFYUI_PORT=8188 \
    MODELS_DIR=/runpod-volume/ComfyUI/models

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git git-lfs aria2 wget curl ca-certificates unzip \
        ffmpeg libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
        python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# ============ COMFYUI + dependencies ============
RUN git clone --depth=1 https://github.com/comfyanonymous/ComfyUI.git /comfyui && \
    cd /comfyui && \
    python3 -m pip install --no-cache-dir -r requirements.txt

# Balikkan pin torch ke CUDA 12.1 supaya cocok dengan driver
RUN python3 -m pip install --no-cache-dir --force-reinstall \
    torch==2.4.1 \
    torchvision==0.19.1 \
    torchaudio==2.4.1 \
    --index-url https://download.pytorch.org/whl/cu121

# Install dependency tambahan (sqlalchemy, alembic, dll)
RUN python3 -m pip install --no-cache-dir \
    sqlalchemy \
    aiosqlite \
    aiohttp \
    alembic \
    blake3 \
    xformers \
    einops \
    einops-exts \
    ftfy \
    regex \
    safetensors \
    sentencepiece \
    protobuf \
    accelerate \
    transformers \
    diffusers \
    av \
    opencv-python-headless \
    librosa \
    soundfile \
    psutil \
    omegaconf \
    timm \
    pydantic \
    python-dotenv \
    || true

# ============ CUSTOM NODES ============
RUN mkdir -p /comfyui/custom_nodes && cd /comfyui/custom_nodes && \
    (git clone --depth=1 https://github.com/kijai/ComfyUI-WanVideoWrapper.git || echo "FAILED: WanVideoWrapper") && \
    (git clone --depth=1 https://github.com/city96/ComfyUI-GGUF.git || echo "FAILED: ComfyUI-GGUF") && \
    (git clone --depth=1 https://github.com/kijai/ComfyUI-KJNodes.git || echo "FAILED: KJNodes") && \
    (git clone --depth=1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git || echo "FAILED: VideoHelperSuite") && \
    (git clone --depth=1 https://github.com/kijai/ComfyUI-MMAudio.git || echo "FAILED: MMAudio") && \
    (git clone --depth=1 https://github.com/sipherxyz/comfyui-art-venture.git || echo "FAILED: art-venture") && \
    (git clone --depth=1 https://github.com/cubiq/ComfyUI_essentials.git || echo "FAILED: essentials") && \
    (git clone --depth=1 https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet.git || echo "FAILED: Advanced-ControlNet") && \
    (git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Impact-Pack.git || echo "FAILED: Impact-Pack") && \
    (git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Manager.git || echo "FAILED: Manager") && \
    (git clone --depth=1 https://github.com/jags111/efficiency-nodes-comfyui.git || echo "FAILED: efficiency-nodes") && \
    (git clone --depth=1 https://github.com/rgthree/rgthree-comfy.git || echo "FAILED: rgthree") && \
    (git clone --depth=1 https://github.com/crystian/ComfyUI-Crystools.git || echo "FAILED: Crystools") && \
    (git clone --depth=1 https://github.com/Jordach/comfy-plasma.git || echo "FAILED: comfy-plasma")

# Install requirements custom nodes
RUN cd /comfyui/custom_nodes && \
    for d in */; do \
      if [ -f "$d/requirements.txt" ]; then \
        python3 -m pip install --no-cache-dir -r "$d/requirements.txt" || echo "skip $d requirements"; \
      fi; \
    done

# ============ MODEL PATH → NETWORK VOLUME ============
RUN rm -rf /comfyui/models && \
    ln -s /runpod-volume/ComfyUI/models /comfyui/models

# ============ BACKEND APP ============
COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /app/requirements.txt || true

COPY handler.py /app/handler.py
COPY workflow_downloader.py /app/workflow_downloader.py
COPY workflow_converter.py /app/workflow_converter.py
COPY download_models.py /app/download_models.py
COPY loras.json /app/loras.json
COPY node_map.json /app/node_map.json
COPY inspect_workflow.py /app/inspect_workflow.py

# ============ NONAKTIFKAN ENTRYPOINT ============
ENTRYPOINT []

WORKDIR /app
CMD ["python3", "-u", "handler.py"]
