#!/usr/bin/env python3
"""Common utilities for legal-ocr engines: retry, error classification, caching."""
import time
import httpx

class PaddleOCRRateLimited(Exception):
    pass

def retry_with_backoff(func, attempts=3, base_delay=1.0, max_delay=30.0):
    last_error = None
    for attempt in range(attempts):
        try:
            return func()
        except httpx.RequestError as e:
            last_error = e
            if attempt < attempts - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(delay)
    raise last_error

def is_transient_httpx_error(error):
    return isinstance(error, httpx.RequestError)

def is_transient_http_status(status_code):
    return status_code == 429 or status_code >= 500

def is_paddle_rate_limited_response(data):
    return isinstance(data, dict) and data.get('code') == 10010
