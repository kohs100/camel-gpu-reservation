from fastapi import HTTPException

import paramiko

SSH_HOSTNAME = "192.168.1.10"

class Auth:
    __create_key = object()

    @classmethod
    def login(cls, username: str, password: str) -> "Auth":
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_client.connect(SSH_HOSTNAME, username=username, password=password)
            ssh_client.close()
            return Auth(cls.__create_key, username, password)
        except paramiko.AuthenticationException:
            raise HTTPException(
                status_code=401, detail={"message": "Authorization failed."}
            )

    def __init__(self, create_key: object, username: str, password: str):
        if create_key is not Auth.__create_key:
            raise TypeError("Auth objects must be created using Auth.login")

        self.username = username
        self.password = password
