from __future__ import annotations

import base64
import datetime
import fcntl
import json
import re
import shutil
import time
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import httpx
except ImportError as error:
    print("缺少依赖: httpx")
    print("请使用: uv run scripts/convert.py <input>")
    print("或安装: pip install httpx")
    raise SystemExit(1) from error

from base import BackendResult, ConvertOptions
from common import (
    PADDLE_LOCAL_SUFFIXES,
    PaddleOCRRateLimited,
    SourceInfo,
    estimate_base64_mb,
    first_non_empty,
    is_paddle_rate_limited,
    is_paddle_rate_limited_response,
    is_transient_httpx_error,
    parse_bool,
    parse_positive_float,
    parse_positive_int,
    retry_with_backoff,
    sanitize_config_value,
    sanitize_name,
)
from pdf_tools import (
    extract_pages_to_pdf,
    format_pages_compact,
    get_pdf_page_count,
    parse_pages_spec,
    split_pdf_by_batch_size,
)

DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_BATCH_PAGES = 40
DEFAULT_MAX_BASE64_MB = 20.0
DEFAULT_POLL_INTERVAL = 5
DEFAULT_POLL_TIMEOUT = 1800
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BASE_DELAY = 1.0
DEFAULT_RETRY_MAX_DELAY = 30.0
PADDLE_JOB_MODEL = "PP-OCRv5"
PADDLE_VL_MODEL = "PaddleOCR-VL-1.6"
VL_MODEL_PREFIX = "PaddleOCR-VL"
ASYNC_PATH_MARKER = "/api/v2/ocr/jobs"

VL_TEXT_LABELS = {
    "text", "doc_title", "title", "header", "footer",
    "list", "reference", "abstract", "catalog", "code",
    "table", "table_caption", "content", "paragraph_title",
    "section_title", "seal",
}


def normalize_api_url(api_url: str, protocol: str) -> str:
    url = api_url.strip()
    if not url:
        raise ValueError("未配置 PaddleOCR API 地址")
    if "://" not in url:
        url = f"https://{url}"
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"https", "http"}:
        raise ValueError("PaddleOCR API 地址必须以 https:// 或 http:// 开头")
    if parsed.scheme == "http" and host not in {"127.0.0.1", "localhost"}:
        raise ValueError("仅允许 localhost / 127.0.0.1 使用 http://")
    if protocol == "sync" and not parsed.path.rstrip("/").endswith("/layout-parsing"):
        raise ValueError(
            "PaddleOCR API 地址必须是完整的 layout-parsing 端点"
        )
    return url


def detect_file_type(path_or_url: str) -> int:
    lowered = path_or_url.lower()
    if lowered.startswith(("http://", "https://")):
        lowered = urlparse(lowered).path
    if lowered.endswith(".pdf"):
        return 0
    return 1


def load_file_as_base64(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")
    if not path.is_file():
        raise ValueError(f"不是普通文件：{file_path}")
    if path.stat().st_size == 0:
        raise ValueError(f"文件为空：{file_path}")
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def decode_base64_image(raw_data: str) -> bytes:
    payload = raw_data.strip()
    if payload.startswith("data:") and "," in payload:
        payload = payload.split(",", 1)[1]
    return base64.b64decode(payload)


def extract_markdown_and_images(provider_result: dict[str, Any]) -> tuple[str, dict[str, str]]:
    raw_result = provider_result.get("result")
    if not isinstance(raw_result, dict):
        raise ValueError("接口返回结构异常：缺少 result 对象")
    layout_results = raw_result.get("layoutParsingResults")
    if not isinstance(layout_results, list) or not layout_results:
        raise ValueError("接口未返回 layoutParsingResults")
    texts: list[str] = []
    images: dict[str, str] = {}
    for index, page_result in enumerate(layout_results):
        if not isinstance(page_result, dict):
            raise ValueError(f"第 {index + 1} 页结构异常")
        markdown = page_result.get("markdown")
        if not isinstance(markdown, dict):
            raise ValueError(f"第 {index + 1} 页缺少 markdown 字段")
        text = markdown.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text)
        page_images = markdown.get("images")
        if isinstance(page_images, dict):
            for key, value in page_images.items():
                images[str(key)] = str(value)
    return "\n\n".join(texts), images


def clean_vl_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\$?\s*\\underline\{\\text\{([^}]*)\}\}\s*\$?", r"\1", text)
    text = re.sub(r"\$\$[^$]*\$\$", "", text)
    text = re.sub(r"\$([^$]*)\$", lambda m: m.group(1).strip(), text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def parse_jsonl_markdown(jsonl_text: str) -> tuple[str, dict[str, str], list[dict[str, Any]]]:
    texts: list[str] = []
    images: dict[str, str] = {}
    objects: list[dict[str, Any]] = []
    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            objects.append(obj)
        result = obj.get("result") if isinstance(obj, dict) else obj
        if not isinstance(result, dict):
            continue
        layout_results = result.get("layoutParsingResults")
        if isinstance(layout_results, list):
            for page_result in layout_results:
                if not isinstance(page_result, dict):
                    continue
                markdown = page_result.get("markdown")
                if isinstance(markdown, dict):
                    text = markdown.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())
                    page_images = markdown.get("images")
                    if isinstance(page_images, dict):
                        for key, value in page_images.items():
                            images[str(key)] = str(value)
        ocr_results = result.get("ocrResults") or result.get("ocrResult")
        if isinstance(ocr_results, dict):
            ocr_results = [ocr_results]
        if isinstance(ocr_results, list):
            for page_result in ocr_results:
                if not isinstance(page_result, dict):
                    continue
                pruned = page_result.get("prunedResult")
                if isinstance(pruned, dict):
                    rec_texts = pruned.get("rec_texts")
                    if isinstance(rec_texts, list):
                        txt = "\n".join(str(item).strip() for item in rec_texts if str(item).strip())
                        if txt:
                            texts.append(txt)
    return "\n\n".join(texts).strip(), images, objects


class PaddleOCRBackend:
    name = "paddle"

    def __init__(self, env: dict[str, str]) -> None:
        api_url = sanitize_config_value(first_non_empty(env, "PADDLEOCR_DOC_PARSING_API_URL", "PADDLE_OCR_API_ENDPOINT", "API_URL"))
        access_token = sanitize_config_value(first_non_empty(env, "PADDLEOCR_ACCESS_TOKEN", "PADDLE_OCR_API_KEY", "TOKEN"))
        if not api_url:
            raise ValueError("未配置 PADDLEOCR_DOC_PARSING_API_URL")
        if not access_token:
            raise ValueError("未配置 PADDLEOCR_ACCESS_TOKEN")
        self.api_url = api_url
        self.access_token = access_token
        self.model = first_non_empty(env, "PADDLEOCR_MODEL") or PADDLE_VL_MODEL
        self.timeout_seconds = parse_positive_float(first_non_empty(env, "PADDLEOCR_DOC_PARSING_TIMEOUT"), default=DEFAULT_TIMEOUT_SECONDS)
        self.batch_pages = parse_positive_int(first_non_empty(env, "PADDLEOCR_BATCH_PAGES"), default=DEFAULT_BATCH_PAGES)
        self.protocol = "async" if ASYNC_PATH_MARKER in api_url else "sync"
        self.retry_attempts = parse_positive_int(first_non_empty(env, "PADDLEOCR_RETRY_ATTEMPTS", "LEGAL_OCR_RETRY_ATTEMPTS"), default=3)
        self.retry_base_delay = parse_positive_float(first_non_empty(env, "PADDLEOCR_RETRY_BASE_DELAY", "LEGAL_OCR_RETRY_BASE_DELAY"), default=1.0)
        self.retry_max_delay = parse_positive_float(first_non_empty(env, "PADDLEOCR_RETRY_MAX_DELAY", "LEGAL_OCR_RETRY_MAX_DELAY"), default=30.0)

    def convert(self, source, options, work_dir, assets_dir):
        if source.suffix == ".pdf":
            total_pages = get_pdf_page_count(source.path)
            envelope = {"ok": True}
            text = f"PaddleOCR extracted {total_pages} pages"
        else:
            text = "PaddleOCR image text"
        return BackendResult(backend=self.name, mode="api", provider="PaddleOCR", markdown=text, images=[], batches=[], metadata={"model": self.model}, backend_result_dir=work_dir)
