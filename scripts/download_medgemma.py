import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = os.environ.get("LOCAL_MEDGEMMA_MODEL_ID", "google/medgemma-1.5-4b-it")
MODEL_DIR = Path(
    os.environ.get(
        "LOCAL_MEDGEMMA_MODEL_DIR",
        PROJECT_ROOT / "models" / "medgemma-1.5-4b-it",
    )
)


def main() -> int:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print("Set HF_TOKEN in the current shell before downloading.", file=sys.stderr)
        return 2

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=MODEL_DIR,
        local_dir_use_symlinks=False,
        token=token,
        resume_download=True,
    )
    print(f"Downloaded {MODEL_ID} to {MODEL_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
