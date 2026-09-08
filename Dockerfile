FROM runpod/worker-comfyui:main-base

ENV COMFYUI_DIR=/comfyui \
    COMFYUI_PORT=8188 \
    MODELS_DIR=/runpod-volume/ComfyUI/models

WORKDIR /app

# ============ PASTIKAN GIT TERSEDIA ============
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# ============ CUSTOM NODES (tahan banting) ============
RUN mkdir -p ${COMFYUI_DIR}/custom_nodes && cd ${COMFYUI_DIR}/custom_nodes && \
    (git clone --depth=1 https://github.com/kijai/ComfyUI-WanVideoWrapper.git || echo "FAILED: WanVideoWrapper") && \
    (git clone --depth=1 https://github.com/city96/ComfyUI-GGUF.git || echo "FAILED: ComfyUI-GGUF") && \
     git clone https://github.com/kijai/ComfyUI-KJNodes.git && \
    (git clone --depth=1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git || echo "FAILED: VideoHelperSuite") && \
    (git clone --depth=1 https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git || echo "FAILED: Frame-Interpolation") && \
    (git clone --depth=1 https://github.com/kijai/ComfyUI-MMAudio.git || echo "FAILED: MMaAudio") && \
    (git clone --depth=1 https://github.com/sipherxyz/comfyui-art-venture.git || echo "FAILED: art-venture") && \
    (git clone --depth=1 https://github.com/cubiq/ComfyUI_essentials.git || echo "FAILED: essentials") && \
    (git clone --depth=1 https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet.git || echo "FAILED: Advanced-ControlNet") && \
    (git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Impact-Pack.git || echo "FAILED: Impact-Pack") && \
    (git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Manager.git || echo "FAILED: Manager") && \
    (git clone --depth=1 https://github.com/jags111/efficiency-nodes-comfyui.git || echo "FAILED: efficiency-nodes") && \
    (git clone --depth=1 https://github.com/rgthree/rgthree-comfy.git || echo "FAILED: rgthree") && \
    (git clone --depth=1 https://github.com/crystian/ComfyUI-Crystools.git || echo "FAILED: Crystools") && \
    (git clone --depth=1 https://github.com/Jordach/comfy-plasma.git || echo "FAILED: comfy-plasma")

# Install requirements tiap custom node (jangan gagal build)
RUN cd ${COMFYUI_DIR}/custom_nodes && \
    for d in */; do \
      if [ -f "$d/requirements.txt" ]; then \
        python3 -m pip install --no-cache-dir -r "$d/requirements.txt" || echo "skip $d requirements"; \
      fi; \
    done

# ============ MODEL PATH → NETWORK VOLUME ============
RUN rm -rf ${COMFYUI_DIR}/models && \
    ln -s /runpod-volume/ComfyUI/models ${COMFYUI_DIR}/models

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

# ============ NONAKTIFKAN ENTRYPOINT BAWAAN ============
ENTRYPOINT []

WORKDIR /app
CMD ["python3", "-u", "handler.py"]
