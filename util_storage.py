import json
import types
import time

from typing import Optional, Dict, Type, List
from pydantic import BaseModel
from filelock import FileLock

from util_auth import Auth

STORAGE_PATH = "/root/services/gpu-rent/storage.json"
STORAGE_LOCK_PATH = "/root/services/gpu-rent/storage.json.lock"

lock = FileLock(STORAGE_LOCK_PATH, timeout=10)

class GPUStatus(BaseModel):
    invalid_until: float
    user: Optional[str]

    def sanitize(self):
        assert (self.user is None) == (self.invalid_until == 0)

    def is_available(self, current: Optional[float] = None):
        if current is None:
            current = time.time()

        if self.user is None:
            assert self.invalid_until == 0
            return True
        else:
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
        assert self.invalid_until > 0

        self.unsafe_release()

    def unsafe_release(self):
        self.sanitize()

        self.invalid_until = 0
        self.user = None


class Storage(BaseModel):
    gpu_status: Dict[str, GPUStatus]
    port_mapping: Dict[str, int]

    def check_availability(self, auth: Auth, gpus: List[str]) -> bool:
        for gid in gpus:
            gstate = self.gpu_status[gid]
            if not gstate.is_occupied_by(auth.username) and not gstate.is_available():
                return False
        return True

    # Return kill user list
    def acquire(self, auth: Auth, gpus: List[str], reserve_time: float) -> List[str]:
        assert self.check_availability(auth, gpus)

        kill_user_list: List[str] = []
        for gid, gstate in self.gpu_status.items():
            if gid in gpus:
                old_user = gstate.user
                if old_user is not None:
                    # Kill preemptible containers
                    do_kill = self.release(old_user)
                    if do_kill:
                        kill_user_list.append(old_user)
                gstate.reserve(auth, reserve_time)
            else:
                if gstate.user == auth.username:
                    gstate.release(auth)

        return kill_user_list

    # If true, container must be killed.
    def release(self, user: str) -> bool:
        found = False
        for gstate in self.gpu_status.values():
            if gstate.user == user:
                assert gstate.invalid_until > 0, "SANITY"
                gstate.unsafe_release()
                found = True
        return found


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
