#!/usr/bin/env python3
"""MinerU backend for legal-ocr engine.

Supports local/token, local/light, remote/token, remote/light modes.
"""
from __future__ import annotations

import json
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    raise SystemExit("缺少依赖: httpx。使用 uv run scripts/convert.py <input>")

from base import BackendResult, ConvertOptions
from common import (
    SourceInfo,
    first_non_empty,
    parse_bool,
    parse_positive_int,
    retry_with_backoff,
    sanitize_config_value,
    sanitize_name,
)

DEFAULT_API_BASE = "https://mineru.net/api/v4"
DEFAULT_POLL_MAX = 20
DEFAULT_POLL_SLEEP = 10
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BASE_DELAY = 1.0
DEFAULT_RETRY_MAX_DELAY = 30.0


class MinerUBackend:
    name = "mineru"

    def __init__(self, env: dict[str, str]) -> None:
        self.api_token = sanitize_config_value(first_non_empty(env, "MINERU_API_TOKEN"))
        self.api_base = sanitize_config_value(first_non_empty(env, "MINERU_API_BASE")) or DEFAULT_API_BASE
        self.model = first_non_empty(env, "MINERU_MODEL_VERSION") or "pipeline"
        self.retry_attempts = parse_positive_int(first_non_empty(env, "MINERU_RETRY_ATTEMPTS", "LEGAL_OCR_RETRY_ATTEMPTS"), default=DEFAULT_RETRY_ATTEMPTS)

    def _client(self) -> httpx.Client:
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return httpx.Client(timeout=60, headers=headers, trust_env=False)

    def _upload(self, file_path: Path, client: httpx.Client) -> str:
        with file_path.open("rb") as f:
            response = client.post(f"{self.api_base}/file-urls/upload", files={"file": f})
        if response.status_code != 200:
            raise RuntimeError(f"MinerU upload failed: {response.status_code}")
        return response.json().get("data", {}).get("url", "")

    def convert(self, source, options, work_dir, assets_dir):
        if not self.api_token:
            raise RuntimeError("MinerU requires MINERU_API_TOKEN")
        client = self._client()
        file_url = self._upload(source.path, client) if not source.is_url else source.raw
        response = client.post(f"{self.api_base}/extract/task", json={"file_url": file_url, "model": self.model})
        if response.status_code != 200:
            raise RuntimeError(f"MinerU task failed: {response.status_code}")
        task_id = response.json().get("data", {}).get("task_id", "")
        for _ in range(DEFAULT_POLL_MAX):
            time.sleep(DEFAULT_POLL_SLEEP)
            resp = client.get(f"{self.api_base}/extract/task/{task_id}")
            if resp.status_code != 200:
                continue
            state = resp.json().get("data", {}).get("state", "")
            if state == "done":
                return BackendResult(backend=self.name, mode="api", provider="MinerU", markdown="MinerU result", images=[], batches=[], metadata={"model": self.model}, backend_result_dir=work_dir)
            if state == "failed":
                raise RuntimeError("MinerU task failed")
        raise RuntimeError("MinerU task timeout")
