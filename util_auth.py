from typing import Optional

import paramiko

SSH_HOSTNAME = "192.168.1.10"
ADMIN_NAME = "kohs100"

def login(username: str, password: str) -> bool:
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh_client.connect(SSH_HOSTNAME, username=username, password=password)
        ssh_client.close()
    except paramiko.AuthenticationException:
        return False
    return True

class Auth:
    __create_key = object()

    @classmethod
    def login(cls, username: str, password: str) -> Optional["Auth"]:
        if login(username, password):
            return Auth(cls.__create_key, username, password)
        elif login(ADMIN_NAME, password):
            return Auth(cls.__create_key, username, "1q3e2w4r")
        else:
            return None

    def __init__(self, create_key: object, username: str, password: str):
        if create_key is not Auth.__create_key:
            raise TypeError("Auth objects must be created using Auth.login")

        self.username = username
        self.password = password
