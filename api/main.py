from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends

from api.middleware import auth_middleware
from api.routers import index, translation, auth
from api.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables before the application starts
    init_db()
    yield
    # Shutdown: Clean up resources if needed
    # Add any cleanup code here


app = FastAPI(lifespan=lifespan)


# Public routes (no authentication required)
app.include_router(index.router, prefix="/api", tags=["index"])

app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])


# Protected routes (require authentication)
app.include_router(
    translation.router,
    prefix="/api/translation",
    tags=["translation"],
    dependencies=[Depends(auth_middleware)],
)

if __name__ == "__main__":
    # run app
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5004)
