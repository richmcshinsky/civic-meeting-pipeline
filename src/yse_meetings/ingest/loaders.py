"""Fetch loaders referenced by source configs.

Each loader knows how to pull raw rows for one kind of source. Adding a new
source of an existing kind (another Hugging Face dataset, another Dataverse
parquet release) is a config change. A genuinely new transport is one new
function here.
"""

from __future__ import annotations

import json
from pathlib import Path

DATAVERSE_ACCESS = "https://dataverse.harvard.edu/api/access/datafile/{file_id}"


def huggingface_streaming(params: dict, raw_dir: Path) -> list[dict]:
    """Stream a sample of rows from a Hugging Face dataset to jsonl."""
    out_dir = raw_dir / params["name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sample.jsonl"

    if not out_path.exists():
        from datasets import load_dataset

        ds = load_dataset(params["dataset"], split=params.get("split", "train"),
                          streaming=True)
        with out_path.open("w", encoding="utf-8") as f:
            for i, row in enumerate(ds):
                if i >= params.get("sample_size", 200):
                    break
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return [json.loads(line) for line in out_path.open(encoding="utf-8")]


def dataverse_parquet(params: dict, raw_dir: Path):
    """Download one or more yearly parquet files from Harvard Dataverse."""
    import pandas as pd
    import requests

    out_dir = raw_dir / params["name"]
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    file_ids: dict = params["file_ids"]
    for year in params["years"]:
        file_id = file_ids.get(str(year))
        if file_id is None:
            continue
        path = out_dir / f"meetings.{year}.parquet"
        if not path.exists():
            url = DATAVERSE_ACCESS.format(file_id=file_id)
            with requests.get(url, stream=True, timeout=180) as r:
                r.raise_for_status()
                with path.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
        frames.append(pd.read_parquet(path, columns=params.get("columns")))

    if not frames:
        raise RuntimeError(f"No files loaded for {params['name']}")
    return pd.concat(frames, ignore_index=True)


LOADERS = {
    "huggingface_streaming": huggingface_streaming,
    "dataverse_parquet": dataverse_parquet,
}
