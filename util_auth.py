import paramiko
from typing import Optional, Any

SSH_HOSTNAME = "192.168.1.10"


class Auth:
    __create_key = object()

    @classmethod
    def login(cls, user: str, passwd: str) -> Optional["Auth"]:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_client.connect(SSH_HOSTNAME, username=user, password=passwd)
            ssh_client.close()
            return Auth(cls.__create_key, user, passwd)
        except paramiko.AuthenticationException:
            return None

    def __init__(self, create_key: Any, user: str, passwd: str):
        if create_key is not Auth.__create_key:
            raise TypeError("Auth objects must be created using Auth.login")

        self.username = user
        self.password = passwd
