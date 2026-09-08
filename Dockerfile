FROM runpod/worker-comfyui:main-base

ENV COMFYUI_DIR=/comfyui \
    COMFYUI_PORT=8188 \
    MODELS_DIR=/runpod-volume/ComfyUI/models

WORKDIR /app

# ============ CUSTOM NODES WAJIB ============
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

# Install requirements tiap custom node
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

# ============ PENTING: Nonaktifkan entrypoint bawaan ============
ENTRYPOINT []

WORKDIR /app
CMD ["python3", "-u", "handler.py"]
