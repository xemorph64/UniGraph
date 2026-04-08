from fastapi import APIRouter

router = APIRouter()


@router.get("/ws/status")
async def websocket_status() -> dict:
    return {"status": "ready"}
