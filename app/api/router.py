from fastapi import APIRouter
from app.api import auth, health, jobs, podcasts, notebooks

api_router = APIRouter()

# Register module endpoints
api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(jobs.router)
api_router.include_router(podcasts.router)
api_router.include_router(notebooks.router)
