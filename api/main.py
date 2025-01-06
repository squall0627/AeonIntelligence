from contextlib import asynccontextmanager

from fastapi.exceptions import RequestValidationError
from fastapi import (
    FastAPI,
    Request,
    Depends,
)
from fastapi.responses import JSONResponse

from api.cache.redis_handler import get_redis

from api.middleware import auth_middleware
from api.routers import index, translation, auth, user_settings
from api.db.database import init_db
from core.utils.log_handler import rotating_file_logger

logger = rotating_file_logger("translation_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables before the application starts
    init_db()
    yield
    # Shutdown: Clean up resources if needed
    # Add any cleanup code here


app = FastAPI(lifespan=lifespan)


# Exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error for request: {request.url}")
    logger.error(f"Error details: {exc.errors()}")
    # logger.error(f"Request body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


# Public routes (no authentication required)
app.include_router(index.router, prefix="/api", tags=["index"])

app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])


# Protected routes (require authentication)
app.include_router(
    translation.router,
    prefix="/api/translation",
    tags=["translation"],
    dependencies=[Depends(auth_middleware), Depends(get_redis)],
)

app.include_router(
    user_settings.router,
    prefix="/api/user/settings",
    tags=["user_settings"],
    dependencies=[Depends(auth_middleware), Depends(get_redis)],
)

if __name__ == "__main__":
    # run app
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5004)
