from fastapi import APIRouter
from app.api import auth

api_router = APIRouter()

# Register auth module endpoints
api_router.include_router(auth.router)
