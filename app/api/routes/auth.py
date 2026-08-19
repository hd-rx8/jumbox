from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_auth_service, get_current_user
from app.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.application.auth_service import AuthService
from app.application.exceptions import AuthenticationError, ConflictError
from app.domain.auth import AuthenticatedUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Public endpoint to create a user account and receive a JWT access token.",
    responses={
        409: {"description": "Email already registered"},
    },
)
async def register(payload: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    try:
        result = await auth_service.register(
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return TokenResponse(access_token=result.access_token, token_type=result.token_type)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password",
    description="Public endpoint to exchange user credentials for a JWT access token.",
    responses={
        401: {"description": "Invalid email or password"},
    },
)
async def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    try:
        result = await auth_service.login(email=payload.email, password=payload.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse(access_token=result.access_token, token_type=result.token_type)


@router.get(
    "/me",
    summary="Get current user profile",
    description="Protected endpoint returning the profile of the currently authenticated user.",
    responses={
        401: {"description": "Not authenticated or invalid token"},
    },
)
async def me(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    return {"user_id": str(current_user.user_id), "email": current_user.email, "is_admin": current_user.is_admin}
