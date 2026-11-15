"""Streaming HTTP download with progress. The only network code in Chatport."""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger("chatport.tools")

CHUNK = 256 * 1024


class DownloadError(Exception):
    """Raised when the HTTP request or the transfer fails. The cause is chained."""


def download_file(
    url: str,
    target: Path,
    on_progress: Callable[[int, int], None],
    timeout: float = 60,
) -> None:
    """Stream ``url`` into ``target``, calling ``on_progress(done, total)`` per chunk.

    ``total`` is 0 when the server does not send Content-Length.
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    log.info("downloading %s", url)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            total = _content_length(response)
            done = 0
            with target.open("wb") as out:
                on_progress(0, total)
                while True:
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    on_progress(done, total)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as exc:
        _discard(target)
        raise DownloadError(f"download failed: {url}: {exc}") from exc
    log.info("downloaded %s (%d bytes)", target.name, target.stat().st_size)


def _content_length(response: object) -> int:
    headers = getattr(response, "headers", None)
    raw = headers.get("Content-Length") if headers is not None else None
    try:
        return max(int(raw), 0) if raw else 0
    except (TypeError, ValueError):
        return 0


def _discard(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        log.debug("could not remove partial file %s", path)
