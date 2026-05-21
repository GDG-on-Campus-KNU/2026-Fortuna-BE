from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from app.core.database import engine, Base
from app.api.router import api_router

# Import user model to ensure it is registered on Base.metadata
from app.models.user import User  # noqa


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create database tables on startup (very useful for development)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Dispose of connection pools on shutdown
    await engine.dispose()


app = FastAPI(
    title="Fortuna API",
    description="2026 Fortuna Backend API with secure async authentication",
    lifespan=lifespan,
)

# Register versioned API router
app.include_router(api_router, prefix="/api/v1")


class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None


@app.get("/")
def read_root():
    return {"message": "Welcome to 2026 Fortuna API"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}


@app.post("/items/")
def create_item(item: Item):
    return {"item": item, "message": "Item created successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
