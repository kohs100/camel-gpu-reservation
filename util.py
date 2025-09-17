from typing import List, Optional

from util_auth import Auth
from util_storage import StorageCtx
from util_container import UnsafeContainer
from util_types import ReservationReqData

MAX_PORT = 11000

class AuthorizedContainer(UnsafeContainer):
    def __init__(self, auth: Auth):
        self.auth = auth
        super().__init__(auth.username)

    def get_port(self) -> int:
        with StorageCtx(readonly=False) as storage:
            if self.user in storage.port_mapping:
                port = storage.port_mapping[self.user]
                assert port < 65535, "Invalid port number encoutered"
                return port
            else:
                ports = storage.port_mapping.values()
                set_ports = set(ports)
                assert len(set_ports) == len(
                    ports
                ), "Duplicated port assignment detected"
                new_port = max(set_ports) + 1
                assert (
                    new_port < MAX_PORT
                ), f"Invalid port number encountered: {new_port}"
                storage.port_mapping[self.user] = new_port
                return new_port

    def run(self, privileged: bool, gpus: List[str]):
        self.unsafe_run(privileged, gpus, self.auth.password, self.get_port())


def release_gpus(auth: Auth):
    # Release: action-first
    AuthorizedContainer(auth).kill()

    # Release: metadata-last
    with StorageCtx(readonly=False) as storage:
        storage.release(auth.username)

# GPU 할당의 정신적 모델
# 1. 예약 시간동안의 GPU의 독점 사용을 보장한다. (RESERVED)
# 2. 예약 시간 이후에도 다른 사용자의 간섭이 없다면 사용권은 유지된다. (PREEMPTIBLE)
# 3. 다른 사용자가 해당 GPU를 사용할 경우 컨테이너는 kill되고 gpu가 회수된다.

def acquire_gpus(req: ReservationReqData, auth: Auth) -> Optional[int]:
    container = AuthorizedContainer(auth)
    port = container.get_port()

    # Acquire: metadata-first
    with StorageCtx(readonly=False) as storage:
        if not storage.check_availability(auth, req.GPUs):
            return None
        shutdown_users = storage.acquire(auth, req.GPUs, req.reservation_time)

    # Acquire: action-last
    for shutdown_user in shutdown_users:
        print(f"  Shutting down illegal container of {shutdown_user}...")
        UnsafeContainer(shutdown_user).kill()

    print(f"  Relaunching...")
    container.kill()
    print(f"  Killed. Re-launching...")
    container.run(req.privileged, req.GPUs)
    print(f"  Launched.")
    return port
