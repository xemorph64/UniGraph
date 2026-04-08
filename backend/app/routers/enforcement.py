from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_enforcement_actions() -> dict:
    return {"items": []}
