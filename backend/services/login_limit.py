from collections import OrderedDict
from threading import Lock
import time

from fastapi import HTTPException

_attempts = OrderedDict()
_lock = Lock()


def check_login_limit(username: str) -> None:
    now = time.monotonic()
    with _lock:
        while _attempts and next(iter(_attempts.values()))[0] <= now - 60:
            _attempts.popitem(last=False)
        start, count = _attempts.get(username, (now, 0))
        if count >= 10 or (username not in _attempts and len(_attempts) >= 10000):
            raise HTTPException(429, "Too many login attempts; retry after one minute", headers={"Retry-After": "60"})
        _attempts[username] = (start, count + 1)
