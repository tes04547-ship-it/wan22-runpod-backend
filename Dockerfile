FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/workspace/hf_cache \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    COMFYUI_DIR=/app/ComfyUI \
    COMFYUI_PORT=8188 \
    MODELS_DIR=/workspace/ComfyUI/models

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git git-lfs aria2 wget curl ca-certificates unzip \
        ffmpeg libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
        build-essential \
        python3 python3-pip python3-dev && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip

# ============ COMFYUI ============
# ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git ${COMFYUI_DIR} && \
    cd ${COMFYUI_DIR} && \
    pip install --no-cache-dir -r requirements.txt

# ============ FIX: Install missing dependencies ============
RUN pip install --no-cache-dir sqlalchemy aiosqlite aiohttp


# ============ FIX: Pin PyTorch ke CUDA 12.1 ============
RUN pip install --no-cache-dir --force-reinstall \
    torch==2.4.1 \
    torchvision==0.19.1 \
    torchaudio==2.4.1 \
    --index-url https://download.pytorch.org/whl/cu121

# ============ CUSTOM NODES WAJIB (sesuai notebook Cell 3) ============
RUN mkdir -p ${COMFYUI_DIR}/custom_nodes && cd ${COMFYUI_DIR}/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/city96/ComfyUI-GGUF.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git && \
    git clone https://github.com/kijai/ComfyUI-MMAudio.git && \
    git clone https://github.com/sipherxyz/comfyui-art-venture.git && \
    git clone https://github.com/cubiq/ComfyUI_essentials.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git && \
    git clone https://github.com/jags111/efficiency-nodes-comfyui.git && \
    git clone https://github.com/rgthree/rgthree-comfy.git && \
    git clone https://github.com/crystian/ComfyUI-Crystools.git && \
    git clone https://github.com/Jordach/comfy-plasma.git

RUN cd ${COMFYUI_DIR}/custom_nodes && \
    for d in */; do \
      if [ -f "$d/requirements.txt" ]; then \
        python3 -m pip install --no-cache-dir -r "$d/requirements.txt" || echo "skip $d requirements"; \
      fi; \
    done

# ============ MODEL PATH → NETWORK VOLUME ============
RUN mkdir -p /runpod-volume/ComfyUI/models && \
    rm -rf ${COMFYUI_DIR}/models && \
    ln -s /runpod-volume/ComfyUI/models ${COMFYUI_DIR}/models

# ============ BACKEND APP ============
COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /app/requirements.txt

COPY handler.py /app/handler.py
COPY workflow_downloader.py /app/workflow_downloader.py
COPY workflow_converter.py /app/workflow_converter.py
COPY download_models.py /app/download_models.py
COPY loras.json /app/loras.json
COPY node_map.json /app/node_map.json
COPY inspect_workflow.py /app/inspect_workflow.py

WORKDIR /app
CMD ["python3", "-u", "handler.py"]
