from __future__ import annotations

import json
from pathlib import Path

DEFAULT_BODY_CACHE_PATH = Path("data/eval/body_cache.jsonl")


def load_body_cache(path: Path = DEFAULT_BODY_CACHE_PATH) -> dict[int, str]:
    if not path.exists():
        return {}
    cache: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cache[int(row["number"])] = row.get("body") or ""
    return cache


def append_body_cache(number: int, body: str, path: Path = DEFAULT_BODY_CACHE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"number": number, "body": body}) + "\n")
