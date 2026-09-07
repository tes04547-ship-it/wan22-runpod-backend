import json

PATH = "/app/workflow_api.json"

with open(PATH, "r") as f:
    wf = json.load(f)

for nid, node in wf.items():
    title = node.get("_meta", {}).get("title", "")
    class_type = node.get("class_type", "")
    print(f"{nid}: {class_type} | title={title}")
