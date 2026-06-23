"""HTTP routes for the users service.

Endpoints are mounted at the root so the gateway can forward
/api/users/{action} -> /{action}, and other services can call directly.
"""
from fastapi import APIRouter, HTTPException, Query

from src.schemas.user_schema import CreateUserRequest, UserResponse
from src.services import user_manager

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "users"}


@router.post("/create", response_model=UserResponse)
def create_user(payload: CreateUserRequest) -> UserResponse:
    user = user_manager.create_user(payload.username)
    return UserResponse(**user)


@router.get("/get", response_model=UserResponse)
def get_user(id: str = Query(..., min_length=1)) -> UserResponse:
    user = user_manager.get_user(id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user)
