import json

PATH = "/app/workflow_api.json"

with open(PATH, "r") as f:
    wf = json.load(f)

for nid, node in wf.items():
    print(f"{nid}: {node.get('class_type')} | title={node.get('_meta', {}).get('title', '')}")
