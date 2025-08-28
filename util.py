from typing import List, Optional

from util_auth import Auth
from util_storage import StorageCtx
from util_container import UnsafeContainer
from util_types import ReleaseReqData, ReservationReqData

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

def release_gpus(req: ReleaseReqData, auth: Auth):
    with StorageCtx(readonly=False) as storage:
        for _gid, gstate in storage.gpu_status.items():
            if gstate.is_occupied_by(req.username):
                gstate.release(auth)
    AuthorizedContainer(auth).kill()

def acquire_gpus(req: ReservationReqData, auth: Auth) -> Optional[int]:
    container = AuthorizedContainer(auth)
    port = container.get_port()

    shutdown_users: List[str] = []
    with StorageCtx(readonly=False) as storage:
        available = True
        is_extension = True
        for gid in req.GPUs:
            if not storage.gpu_status[gid].is_occupied_by(req.username):
                is_extension = False
            if not storage.gpu_status[gid].is_available():
                available = False

        if not is_extension and not available:
            # Reservation is illegal
            return None

        # Reservation is legal
        for gid, gstate in storage.gpu_status.items():
            if gid in req.GPUs:
                # Acquire gpus
                if not gstate.is_available():
                    # Shutdown illegal containers
                    old_user = gstate.user
                    if old_user != req.username:
                        shutdown_users.append(old_user)
                gstate.reserve(auth, req.reservation_time)
            else:
                # Release gpus
                if gstate.is_occupied_by(req.username):
                    gstate.release(auth)

    # Perform actual shutdown operation after storage context released
    for shutdown_user in shutdown_users:
        print(f"  Shutting down illegal container of {shutdown_user}...")
        UnsafeContainer(shutdown_user).kill()

    print(f"  Relaunching...")
    container.kill()
    print(f"  Killed. Re-launching...")
    container.run(req.privileged, req.GPUs)
    print(f"  Launched.")
    return port
