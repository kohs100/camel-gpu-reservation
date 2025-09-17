import subprocess
import os
import shutil

from typing import List, Optional, Literal
from pydantic import BaseModel

BASE_DOCKER_IMAGE = "localhost/image_base"
# BASE_DOCKER_IMAGE = "docker.io/nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04"

PERSISTENT_DATA_DIR = "/root/services/gpu-rent/persistent_data"
IMAGE_PATH = "/root/services/gpu-rent/images"

class PersistentPath(BaseModel):
    container_path: str
    host_path_prefix: str
    template: Optional[str]

    def get_host_path(self, username: str):
        assert not self.host_path_prefix.endswith("/")
        path = f"{self.host_path_prefix}/{username}"
        if not os.path.isdir(path):
            if self.template is None:
                os.makedirs(path)
            else:
                shutil.copytree(self.template, path)
        assert os.path.isdir(path)
        return path


PERSISTENT_PATHS: List[PersistentPath] = [
    PersistentPath(
        container_path="/root",
        host_path_prefix=f"{PERSISTENT_DATA_DIR}/root",
        template=f"{PERSISTENT_DATA_DIR}/template/root",
    ),
    PersistentPath(
        container_path="/home",
        host_path_prefix=f"{PERSISTENT_DATA_DIR}/home",
        template=None,
    ),
    PersistentPath(
        container_path="/data", host_path_prefix=f"/data/gpu-node-data", template=None
    ),
]

ContainerState = Literal["RUNNING", "CREATED", None]

class UnsafeContainer:
    def __init__(self, user: str):
        self.user = user

    @property
    def container_name(self):
        return f"gpu-rent-{self.user}"

    @property
    def image_name(self):
        return f"localhost/image-gpu-rent-{self.user}"

    def does_image_exist(self):
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{.Id}}",
                self.image_name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return b"Error: no such object" not in result.stderr

    def is_created(self):
        return self.get_state() == "RUNNING" or self.get_state() == "CREATED"

    def is_running(self):
        return self.get_state() == "RUNNING"

    def get_port(self) -> int:
        raise NotImplementedError("Cannot get port in unauthorized context")

    def get_state(self) -> ContainerState:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", self.container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if b"Error: no such object" in result.stderr:
            return None
        if b"true" in result.stdout:
            return "RUNNING"
        elif b"false" in result.stdout:
            return "CREATED"
        else:
            raise ValueError(f"Invalid inspection result: {result.stdout.decode()}")

    def kill(self):
        if self.is_running():
            print(f"  Killing {self.container_name}...")
            result = subprocess.run(
                ["docker", "kill", self.container_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if b"Error" in result.stderr:
                raise RuntimeError(f"Kill failed: {result.stderr.decode()}")

        if self.is_created():
            assert not self.is_running(), "Container is not stopped!!"

            print(f"  Exporting {self.container_name}...")
            result = subprocess.run(
                [
                    "docker",
                    "commit",
                    self.container_name,
                    self.image_name,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if b"Error" in result.stderr:
                raise RuntimeError(f"Commit failed: {result.stderr.decode()}")
            result = subprocess.run(
                [
                    "docker",
                    "rm",
                    self.container_name,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if b"Error" in result.stderr:
                raise RuntimeError(f"Remove failed: {result.stderr.decode()}")

    def run_command(self, cmd: str):
        assert self.get_state() == "RUNNING", "Container is not running!"

        result = subprocess.run(
            [
                "podman",
                "exec",
                "--interactive",
                "--tty",
                self.container_name,
                "bash",
                "-c",
                cmd,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert b"Error" not in result.stderr

    def unsafe_run(self, privileged: bool, gpus: List[str], passwd: str, port: int):
        old_state = self.get_state()
        assert old_state is None, f"Container is in invalid state: {old_state}"

        cmd_list = [
            "podman",
            "run",
            "--shm-size=2gb",
            "--detach",
            "--interactive",
            "--tty",
        ]

        # Set privilege
        if privileged:
            cmd_list.append("--privileged")

        # Set container name
        cmd_list += ["--name", self.container_name]

        # Set port mapping
        cmd_list += ["--publish", f"{port}:22"]

        # Set security opt
        # cmd_list += ["--security-opt", "seccomp=unconfined"]
        cmd_list += ["--security-opt", "label=disable"]

        # Set capabilities and device mapping
        for cap in ["audit_write", "sys_chroot"]:
            cmd_list += ["--cap-add", cap]
        for gpu in gpus:
            cmd_list += ["--device", gpu]

        # Set network
        cmd_list += ["--network", "gpu-rent"]

        # Set bind mount
        for ppath in PERSISTENT_PATHS:
            host_path = ppath.get_host_path(self.user)
            container_path = ppath.container_path

            cmd_list += [
                "--volume",
                f"{host_path}:{container_path}",
            ]

        # Check image existence
        exists = self.does_image_exist()
        if exists:
            print("  Deploying existing image...")
            image_name = self.image_name
        else:
            print("  Deploying new base image...")
            image_name = BASE_DOCKER_IMAGE

        cmd_list += [
            image_name,
            "/bin/bash",
        ]
        result = subprocess.run(
            cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if b"Error" in result.stderr:
            msg = result.stderr.decode()
            raise RuntimeError(f"Podman run failed: {msg}")
        if not exists:
            self.run_command(f"echo root:{passwd} | chpasswd")
            self.run_command(f"echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config")
        self.run_command(f"service ssh start")
