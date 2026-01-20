"""
Authentication endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import structlog

from api.database import get_db
from api.models import User, APIKey
from api.schemas import Token, UserCreate, User as UserSchema, APIKey as APIKeySchema, APIKeyCreate
from api.auth import (
    authenticate_user, create_access_token, get_password_hash,
    verify_password, generate_api_key, get_current_user
)
from api.monitoring import track_requests

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=Token)
@track_requests
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access token.
    
    - **username**: User username
    - **password**: User password
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    logger.info(
        "User logged in",
        username=user.username,
        user_id=user.id
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800  # 30 minutes
    }


@router.post("/register", response_model=UserSchema, status_code=201)
@track_requests
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    - **username**: Unique username (min 3 characters)
    - **email**: Valid email address
    - **password**: Password (min 8 characters)
    - **full_name**: Optional full name
    """
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists"
            )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True,
        is_superuser=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(
        "User registered",
        username=user.username,
        email=user.email,
        user_id=user.id
    )
    
    return user


@router.get("/me", response_model=UserSchema)
@track_requests
async def read_users_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information.
    """
    return current_user


@router.post("/api-keys", response_model=APIKeySchema, status_code=201)
@track_requests
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key for the current user.
    
    - **name**: API key name (required)
    - **permissions**: List of permissions (optional)
    - **expires_at**: Expiration date (optional)
    """
    # Generate API key
    raw_key = generate_api_key()
    key_hash = get_password_hash(raw_key)
    
    api_key = APIKey(
        name=api_key_data.name,
        key_hash=key_hash,
        user_id=current_user.id,
        permissions=api_key_data.permissions or ["read"],
        expires_at=api_key_data.expires_at,
        is_active=True
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    logger.info(
        "API key created",
        api_key_id=api_key.id,
        name=api_key.name,
        user_id=current_user.id
    )
    
    # Return the raw key only once during creation
    return APIKeySchema(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,  # Only return raw key on creation
        user_id=api_key.user_id,
        is_active=api_key.is_active,
        permissions=api_key.permissions,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at
    )


@router.get("/api-keys")
@track_requests
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current user.
    """
    api_keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    
    # Don't return the raw key in list view
    return [
        {
            "id": key.id,
            "name": key.name,
            "is_active": key.is_active,
            "permissions": key.permissions,
            "expires_at": key.expires_at,
            "last_used": key.last_used,
            "created_at": key.created_at
        }
        for key in api_keys
    ]


@router.delete("/api-keys/{api_key_id}", status_code=204)
@track_requests
async def revoke_api_key(
    api_key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke an API key.
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == api_key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    db.delete(api_key)
    db.commit()
    
    logger.info(
        "API key revoked",
        api_key_id=api_key_id,
        user_id=current_user.id
    )


@router.post("/change-password")
@track_requests
async def change_password(
    password_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user password.
    
    - **current_password**: Current password
    - **new_password**: New password (min 8 characters)
    """
    current_password = password_data.get("current_password")
    new_password = password_data.get("new_password")
    
    if not current_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password and new password are required"
        )
    
    # Verify current password
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    logger.info(
        "Password changed",
        user_id=current_user.id,
        username=current_user.username
    )
    
    return {"message": "Password changed successfully"}
