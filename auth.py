import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ==========================================
# CONFIGURATION (NFR-3 Security)
# ==========================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# ==========================================
# SECURITY SCHEMES & CONTEXT
# ==========================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[int] = None


# ==========================================
# PASSWORD HELPERS (NFR-3)
# ==========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against the stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generates a bcrypt hash for a plain-text password."""
    return pwd_context.hash(password)


# ==========================================
# JWT TOKEN CREATION (NFR-3)
# ==========================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token containing arbitrary payload data."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ==========================================
# DEPENDENCY INJECTION & VERIFICATION (NFR-3)
# ==========================================

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> TokenData:
    """
    Validates the Bearer token and extracts user details.
    Compatible with both PyJWT 1.x and 2.x exception handling.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "user")
        user_id: int = payload.get("user_id")

        if username is None or user_id is None:
            raise credentials_exception

        return TokenData(username=username, role=role, user_id=user_id)
        
    except (jwt.PyJWTError, Exception):
        raise credentials_exception


def require_roles(allowed_roles: list[str]):
    """
    Dependency factory to restrict access based on user roles.
    Example: Depends(require_roles(["admin", "reviewer"]))
    """
    async def role_checker(current_user: Annotated[TokenData, Depends(get_current_user)]):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your assigned role",
            )
        return current_user

    return role_checker
