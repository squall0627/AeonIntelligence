from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def index():
    return "Hello, This is the Aeon Intelligence API!"
