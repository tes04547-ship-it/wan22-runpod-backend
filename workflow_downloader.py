import os
import zipfile
import subprocess

WORKFLOW_ZIP_URL = (
    "https://huggingface.co/ThirdTimesTheCiarc/workflows/resolve/main/"
    "2105650/2382180/wan22SVI2PRONSFWWorkflowWith10StepsI2VModel_v10.zip"
)

UI_OUT = "/app/workflow_ui.json"


def main():
    zip_path = "/app/workflow.zip"

    if os.path.exists(UI_OUT):
        print("workflow_ui.json sudah ada")
        return

    print("Downloading workflow UI dari HF mirror...")
    subprocess.run(
        f'wget -q -O "{zip_path}" "{WORKFLOW_ZIP_URL}"',
        shell=True,
        check=True,
    )

    chosen = None
    max_size = -1

    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if not name.lower().endswith(".json"):
                continue

            info = z.getinfo(name)
            score = info.file_size

            if "workflow" in name.lower():
                score += 2_000_000_000

            if score > max_size:
                max_size = score
                chosen = name

        if chosen is None:
            raise FileNotFoundError(f"Tidak ada JSON di dalam ZIP: {z.namelist()}")

        with z.open(chosen) as f:
            data = f.read()

    with open(UI_OUT, "wb") as f:
        f.write(data)

    os.remove(zip_path)
    print(f"✅ Workflow UI disimpan: {chosen} -> {UI_OUT}")


if __name__ == "__main__":
    main()
