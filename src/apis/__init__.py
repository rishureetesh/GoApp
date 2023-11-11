from fastapi import APIRouter


#Import all routers
from src.apis.authentication import router as auth_router
from src.apis.users import router as user_router

apis = APIRouter()


#Register all routers
apis.include_router(auth_router)
apis.include_router(user_router)

__all__ = ["apis"]