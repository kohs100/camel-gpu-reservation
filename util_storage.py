import json
import types
import time

from typing import Optional, Dict, Type
from pydantic import BaseModel
from filelock import FileLock

from util_auth import Auth

STORAGE_PATH = "/root/services/gpu-rent/storage.json"
STORAGE_LOCK_PATH = "/root/services/gpu-rent/storage.json.lock"

lock = FileLock(STORAGE_LOCK_PATH, timeout=10)


class GPUStatus(BaseModel):
    invalid_until: float
    user: str

    def is_available(self, current: Optional[float] = None):
        if current is None:
            current = time.time()
        return self.invalid_until < current

    def is_occupied_by(self, user: str, current: Optional[float] = None):
        return self.user == user and not self.is_available(current)

    # Need authorized context
    def reserve_until(self, auth: Auth, until: float, current: Optional[float] = None):
        user = auth.username
        assert self.is_available() or self.is_occupied_by(user, current)
        self.user = user
        self.invalid_until = until

    # Need authorized context
    def reserve(self, auth: Auth, reserve_time: float, current: Optional[float] = None):
        self.reserve_until(auth, time.time() + reserve_time, current)

    # Need authorized context
    def release(self, auth: Auth):
        assert self.user == auth.username
        self.invalid_until = 0


class Storage(BaseModel):
    gpu_status: Dict[str, GPUStatus]
    port_mapping: Dict[str, int]


class StorageCtx:
    def __init__(self, readonly: bool):
        self.readonly = readonly

    def __enter__(self):
        lock.acquire()
        with open(STORAGE_PATH, "rt") as f:
            self.data = Storage.model_validate(json.load(f))
        return self.data

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[types.TracebackType],
    ) -> Optional[bool]:
        if not self.readonly:
            with open(STORAGE_PATH, "wt") as f:
                json.dump(Storage.model_dump(self.data), f, indent=2)
        lock.release()
        return False
