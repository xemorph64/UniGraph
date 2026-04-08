from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_reports() -> dict:
    return {"items": []}
