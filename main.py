from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from util_auth import Auth
from util_types import ReleaseReqData, ReservationReqData, ExtendReqData
from util_storage import StorageCtx
from util import acquire_gpus, release_gpus, AuthorizedContainer

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.post("/api/extend")
async def extend_docker(req: ExtendReqData):
    print(f"Received extension request: {req}")

    auth = Auth.login(req.username, req.password)
    container = AuthorizedContainer(auth)
    if not container.is_running():
        return JSONResponse(
            status_code=404, content={"message": "No running container found."}
        )

    with StorageCtx(readonly=False) as storage:
        found = False
        for _gid, gstate in storage.gpu_status.items():
            if gstate.is_occupied_by(req.username):
                found = True
                gstate.reserve(auth, req.reservation_time)

    if not found:
        return JSONResponse(
            status_code=404,
            content={
                "message": "No active GPU reservation found. Maybe container is in CPU-only mode?"
            },
        )
    else:
        return JSONResponse(
            status_code=200, content={"message": "Reservation extended."}
        )


@app.post("/api/reserve")
async def reserve_docker(req: ReservationReqData):
    print(f"Received reservation request: {req}")

    auth = Auth.login(req.username, req.password)
    acquired_port = acquire_gpus(req, auth)
    if acquired_port is None:
        return JSONResponse(
            status_code=400, content={"message": "Failed to launch container."}
        )
    else:
        return JSONResponse(
            status_code=200,
            content={"message": "Successfully launched.", "port": acquired_port},
        )


@app.post("/api/release")
async def release_docker(req: ReleaseReqData):
    print(f"Received release request: {req}")

    auth = Auth.login(req.username, req.password)
    release_gpus(auth)
    return JSONResponse(status_code=200, content={"message": "Released container."})


@app.post("/api/userstatus")
async def get_user_status(req: ReleaseReqData):
    print(f"Received ustat request: {req}")

    auth = Auth.login(req.username, req.password)
    container = AuthorizedContainer(auth)
    return JSONResponse(
        status_code=200,
        content={
            "message": "OK",
            "created": container.is_created(),
            "running": container.is_running(),
            "imaged": container.does_image_exist(),
            "port": container.get_port(),
        },
    )


@app.get("/api/status", response_class=JSONResponse)
async def get_status():
    with StorageCtx(readonly=True) as storage:
        return JSONResponse(status_code=200, content=storage.model_dump())


@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001)
