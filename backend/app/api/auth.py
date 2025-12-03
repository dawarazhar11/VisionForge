"""
Authentication API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from loguru import logger

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.schemas.auth import Token, UserLogin, RefreshTokenRequest
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    get_user_by_email,
    decode_token,
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    Args:
        user_data: User registration data (email, password, full_name)
        db: Database session

    Returns:
        Created user data (without password)

    Raises:
        HTTPException: If email already registered
    """
    # Check if user already exists
    existing_user = get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user = create_user(
        db=db,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )

    logger.info(f"New user registered: {user.email}")

    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with email and password to get JWT tokens.

    Compatible with OAuth2PasswordRequestForm for Swagger UI.

    Args:
        form_data: Login credentials (username=email, password)
        db: Database session

    Returns:
        Access token and refresh token

    Raises:
        HTTPException: If credentials are invalid
    """
    # OAuth2PasswordRequestForm uses 'username' field, we treat it as email
    user = authenticate_user(db, email=form_data.username, password=form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(f"User logged in: {user.email}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/login/json", response_model=Token)
def login_json(user_login: UserLogin, db: Session = Depends(get_db)):
    """
    Login with JSON body (alternative to form-based login).

    Args:
        user_login: Login credentials (email, password)
        db: Database session

    Returns:
        Access token and refresh token

    Raises:
        HTTPException: If credentials are invalid
    """
    user = authenticate_user(db, email=user_login.email, password=user_login.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(f"User logged in (JSON): {user.email}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Get new access token using refresh token.

    Args:
        refresh_request: Refresh token
        db: Database session

    Returns:
        New access token and refresh token

    Raises:
        HTTPException: If refresh token is invalid
    """
    token_data = decode_token(refresh_request.refresh_token)

    if token_data is None or token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new tokens
    access_token = create_access_token(data={"sub": token_data.user_id})
    new_refresh_token = create_refresh_token(data={"sub": token_data.user_id})

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.

    Args:
        current_user: Authenticated user from token

    Returns:
        Current user data
    """
    return current_user
