from fastapi import APIRouter

from src.api.routers.v1 import addresses, traders

api_router = APIRouter()

api_router.include_router(addresses.router, tags=["addresses"])
api_router.include_router(traders.router, tags=["traders"])
