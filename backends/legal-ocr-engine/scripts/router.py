from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from common import (
    MINERU_LOCAL_SUFFIXES,
    PADDLE_LOCAL_SUFFIXES,
    SourceInfo,
    first_non_empty,
    has_paddle_config,
    resolve_mineru_token,
    sanitize_config_value,
)


OFFICE_SUFFIXES = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}


@dataclass
class RouteDecision:
    preferred: str
    candidates: list[str]
    reason: str
    fallback_allowed: bool = True
    route_path: str = "auto"
    notes: list[str] = field(default_factory=list)


def _mineru_supports(source: SourceInfo) -> bool:
    if source.is_url:
        return True
    return source.suffix in MINERU_LOCAL_SUFFIXES


def _paddle_protocol(env: dict[str, str]) -> str:
    configured = first_non_empty(env, "PADDLEOCR_API_PROTOCOL", "PADDLE_API_PROTOCOL").lower()
    if configured in {"sync", "async"}:
        return configured

    api_url = sanitize_config_value(
        first_non_empty(
            env,
            "PADDLEOCR_DOC_PARSING_API_URL",
            "PADDLE_OCR_API_ENDPOINT",
            "API_URL",
        )
    )
    if api_url and "://" not in api_url:
        api_url = f"https://{api_url}"
    return "sync" if urlparse(api_url).path.rstrip("/").endswith("/layout-parsing") else "async"


def _paddle_supports(source: SourceInfo, env: dict[str, str]) -> bool:
    if source.is_url:
        return (
            source.source_type == "remote_doc_url"
            and source.suffix in PADDLE_LOCAL_SUFFIXES
            and _paddle_protocol(env) == "sync"
        )
    return source.suffix in PADDLE_LOCAL_SUFFIXES


def _append_unique(candidates: list[str], backend: str) -> None:
    if backend not in candidates:
        candidates.append(backend)


def _optimal_candidates(
    source: SourceInfo,
    env: dict[str, str],
    *,
    route_path: str,
    paddle_ready: bool,
    mineru_ready: bool,
    notes: list[str],
) -> list[str]:
    candidates: list[str] = []
    paddle_supports = paddle_ready and _paddle_supports(source, env)
    mineru_supports = _mineru_supports(source)

    if source.source_type == "remote_html_url":
        _append_unique(candidates, "mineru")
        return candidates

    if source.suffix in OFFICE_SUFFIXES:
        if mineru_ready:
            _append_unique(candidates, "mineru")
        return candidates

    if source.is_url:
        if mineru_supports and mineru_ready:
            _append_unique(candidates, "mineru")
        if paddle_supports:
            _append_unique(candidates, "paddle")
        elif paddle_ready and source.suffix in PADDLE_LOCAL_SUFFIXES:
            notes.append("PaddleOCR 异步任务接口不能直接提交远程 URL，远程文档优先使用 MinerU")
        return candidates

    if source.suffix in PADDLE_LOCAL_SUFFIXES:
        if paddle_supports:
            _append_unique(candidates, "paddle")
        if mineru_supports and mineru_ready:
            _append_unique(candidates, "mineru")
        return candidates

    if mineru_supports and mineru_ready:
        _append_unique(candidates, "mineru")
    return candidates


def choose_backend(
    source: SourceInfo,
    env: dict[str, str],
    explicit_backend: str = "auto",
    route_path: str = "auto",
) -> RouteDecision:
    explicit_backend = (explicit_backend or "auto").lower()
    route_path = (route_path or "auto").lower().replace("-", "_")
    if route_path not in {"auto", "direct_ocr", "complex_parse"}:
        raise ValueError("route_path 仅支持 auto/direct_ocr/complex_parse")
    paddle_ready = has_paddle_config(env)
    mineru_ready = bool(resolve_mineru_token(env))

    if explicit_backend in {"paddle", "mineru"}:
        if explicit_backend == "mineru" and not mineru_ready:
            raise ValueError("MinerU Token 未配置，不能调用高精度 extract")
        return RouteDecision(
            preferred=explicit_backend,
            candidates=[explicit_backend],
            reason=f"用户显式指定 {explicit_backend} 后端",
            fallback_allowed=False,
            route_path=route_path,
        )

    notes: list[str] = []

    if paddle_ready and mineru_ready:
        candidates = _optimal_candidates(
            source,
            env,
            route_path=route_path,
            paddle_ready=paddle_ready,
            mineru_ready=mineru_ready,
            notes=notes,
        )
        if not candidates:
            raise ValueError(f"不支持的输入类型：{source.suffix or source.raw}")
        return RouteDecision(
            preferred=candidates[0],
            candidates=candidates,
            reason=f"读取路径={route_path}；PaddleOCR 支持的输入优先 PaddleOCR，失败或不支持时切换 MinerU",
            fallback_allowed=len(candidates) > 1,
            route_path=route_path,
            notes=notes,
        )

    if paddle_ready and not mineru_ready:
        if _paddle_supports(source, env):
            return RouteDecision(
                preferred="paddle",
                candidates=["paddle"],
                reason="未检测到 MinerU Token，直接使用 PaddleOCR",
                fallback_allowed=False,
                route_path=route_path,
                notes=notes,
            )
        raise ValueError(f"当前输入需要 MinerU Token：{source.suffix or source.raw}")

    if mineru_ready and not paddle_ready:
        if not _mineru_supports(source):
            raise ValueError(f"不支持的输入类型：{source.suffix or source.raw}")
        return RouteDecision(
            preferred="mineru",
            candidates=["mineru"],
            reason="仅检测到 MinerU Token/API 配置，所有支持的输入统一使用 MinerU",
            fallback_allowed=False,
            route_path=route_path,
            notes=notes,
        )

    raise ValueError("未检测到 MinerU Token 或可用的 PaddleOCR 配置")
