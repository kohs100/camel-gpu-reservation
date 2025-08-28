from typing import List
from pydantic import BaseModel

class ReleaseReqData(BaseModel):
    username: str
    password: str

class ExtendReqData(BaseModel):
    username: str
    password: str
    reservation_time: float

class ReservationReqData(BaseModel):
    username: str
    password: str
    reservation_time: float
    GPUs: List[str]
    privileged: bool
