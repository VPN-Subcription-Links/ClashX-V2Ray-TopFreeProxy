"""Bounded subscription downloads with structured, content-free diagnostics."""
from dataclasses import dataclass, field
import time

import requests

MAX_BYTES = 5 * 1024 * 1024
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


@dataclass
class FetchResult:
    content: str | None = None
    http_status: int | None = None
    error: str | None = None
    requests: list = field(default_factory=list)


def fetch_subscription(url, max_bytes=MAX_BYTES, max_attempts=3):
    if max_bytes < 1 or not 1 <= max_attempts <= 3:
        raise ValueError('Downloads require a positive size limit and 1 to 3 attempts')
    attempts = []
    for attempt in range(1, max_attempts + 1):
        status, error, retry, content, size = None, None, False, None, 0
        try:
            with requests.get(url, timeout=(5, 20), stream=True) as response:
                status = response.status_code
                if status != 200:
                    error = f'http_{status}'
                    retry = status in RETRYABLE_STATUS
                else:
                    declared = response.headers.get('Content-Length', '')
                    if declared.isdigit() and int(declared) > max_bytes:
                        error = 'response_too_large'
                    else:
                        chunks = []
                        for chunk in response.iter_content(chunk_size=64 * 1024):
                            size += len(chunk)
                            if size > max_bytes:
                                error = 'response_too_large'
                                break
                            chunks.append(chunk)
                        if error is None:
                            content = b''.join(chunks).decode('utf-8-sig')
        except requests.exceptions.SSLError:
            error = 'tls_error'
        except requests.Timeout:
            error, retry = 'timeout', True
        except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError):
            error, retry = 'connection_error', True
        except requests.RequestException:
            error = 'request_error'
        except UnicodeError:
            error = 'invalid_utf8'
        attempts.append({'attempt': attempt, 'http_status': status, 'error': error,
                         'received_bytes': size})
        if error is None:
            return FetchResult(content, status, None, attempts)
        if not retry or attempt == max_attempts:
            print(f'[!] Fetch failed: {url}: {error} ({attempt} request attempts)')
            return FetchResult(None, status, error, attempts)
        time.sleep(attempt)
