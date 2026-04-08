from fastapi import APIRouter

router = APIRouter()


@router.post("/score")
async def score() -> dict:
    return {"status": "ok"}
