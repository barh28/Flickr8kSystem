"""HTTP routes for the users service.

Endpoints are mounted at the root so the gateway can forward
/api/users/{action} -> /{action}, and other services can call directly.
"""
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from shared_libraries.tokens import create_token
from src.schemas.user_schema import (
    AuthResponse,
    CreateUserRequest,
    LoginRequest,
    UserResponse,
)
from src.services import user_manager

router = APIRouter()


def _auth_response(user: dict) -> AuthResponse:
    token = create_token(user["user_id"], user["username"])
    return AuthResponse(user_id=user["user_id"], username=user["username"], token=token)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "users"}


@router.post("/create", response_model=AuthResponse)
def create_user(payload: CreateUserRequest) -> AuthResponse:
    user = user_manager.create_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=400, detail="Username already exists")
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    user = user_manager.authenticate(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return _auth_response(user)


@router.get("/get", response_model=UserResponse)
def get_user(
    id: str = Query(..., min_length=1),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> UserResponse:
    # The gateway always sets X-User-Id from the verified token on external
    # requests, so a user can only read their own record. (Trusted internal
    # service-to-service calls omit the header and are not restricted.)
    if x_user_id is not None and x_user_id != id:
        raise HTTPException(status_code=403, detail="Cannot access another user's data")
    user = user_manager.get_user(id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user)
