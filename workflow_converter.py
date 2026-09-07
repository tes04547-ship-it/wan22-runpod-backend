import json
import time
import requests


def get_object_info(base_url, retries=60, delay=3):
    for i in range(retries):
        try:
            r = requests.get(f"{base_url}/object_info", timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

        if i % 10 == 0:
            print(f"Menunggu object_info... ({i * delay}s)")

        time.sleep(delay)

    raise RuntimeError("ComfyUI object_info tidak tersedia")


def convert_ui_to_api(ui, object_info):
    links_map = {}
    for link in ui.get("links", []):
        if len(link) >= 5:
            links_map[link[0]] = (link[1], link[2])

    api = {}

    for node in ui.get("nodes", []):
        node_id = str(node["id"])
        node_type = node.get("type")

        if node_type not in object_info:
            print(f"⚠️  Node {node_type} tidak ada di object_info, di-skip")
            continue

        info = object_info[node_type].get("input", {})
        required = list(info.get("required", {}).keys())
        optional = list(info.get("optional", {}).keys())
        all_inputs = required + optional

        connection_names = set(
            inp.get("name") for inp in node.get("inputs", [])
        )
        widget_names = [name for name in all_inputs if name not in connection_names]

        inputs = {}

        widget_values = node.get("widgets_values", [])
        for i, val in enumerate(widget_values):
            if i < len(widget_names):
                inputs[widget_names[i]] = val

        for inp in node.get("inputs", []):
            link_id = inp.get("link")
            if link_id is None:
                continue

            src_node_id, src_slot = links_map.get(link_id, (None, None))
            if src_node_id is not None:
                inputs[inp["name"]] = [str(src_node_id), src_slot]

        api[node_id] = {
            "class_type": node_type,
            "inputs": inputs,
        }

    return api


def save_api(ui_path, api_path, base_url, object_info=None):
    if object_info is None:
        object_info = get_object_info(base_url)

    with open(ui_path, "r") as f:
        ui = json.load(f)

    api = convert_ui_to_api(ui, object_info)

    with open(api_path, "w") as f:
        json.dump(api, f, indent=2)

    print(f"✅ API workflow tersimpan: {api_path} ({len(api)} node)")


if __name__ == "__main__":
    import sys

    ui_path = sys.argv[1] if len(sys.argv) > 1 else "/app/workflow_ui.json"
    api_path = sys.argv[2] if len(sys.argv) > 2 else "/app/workflow_api.json"

    save_api(ui_path, api_path, "http://127.0.0.1:8188")
