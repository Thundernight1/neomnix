"""
JWT Authentication Module — Neomnix Platform API.
Handles user registration, login, token issuance, and route protection.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.models import User, SessionLocal, AuditLog

import os

# --- Configuration ---
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 hours
JWT_SECRET_KEY_MIN_LENGTH = 32


def get_jwt_secret_key() -> str:
    value = os.getenv("JWT_SECRET_KEY")
    if value is None or not value.strip():
        raise RuntimeError("JWT_SECRET_KEY environment variable is required.")
    if len(value) < JWT_SECRET_KEY_MIN_LENGTH:
        raise RuntimeError(f"JWT_SECRET_KEY must be at least {JWT_SECRET_KEY_MIN_LENGTH} characters.")
    return value


def init_auth_settings() -> None:
    get_jwt_secret_key()

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- OAuth2 Scheme ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# --- Pydantic Models ---
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str
    force_password_change: bool = False  # Prompts first-login password reset modal

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    role: str = "analyst"

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


# --- Core Functions ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_jwt_secret_key(), algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Decode JWT and return authenticated user. Raises 401 on failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, get_jwt_secret_key(), algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(*roles):
    """Dependency factory: restrict endpoint to specific roles."""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' lacks permission. Required: {', '.join(roles)}"
            )
        return current_user
    return role_checker


def log_audit(db: Session, tenant_id: str, user_email: str, action: str, resource_id: str = None, details: dict = None, ip: str = None):
    entry = AuditLog(
        tenant_id=tenant_id,
        user_email=user_email,
        action=action,
        resource_id=resource_id,
        details=details,
        ip_address=ip
    )
    db.add(entry)
    db.commit()
