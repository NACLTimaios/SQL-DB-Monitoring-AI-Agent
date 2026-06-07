"""Authentication and authorization utilities with database-based user management."""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from pydantic import BaseModel
import jwt

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-please-use-env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


# JWT utilities
def create_access_token(data: dict = None, username: str = None, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if data is None and username:
        data = {"sub": username}
    elif data is None:
        raise ValueError("Either 'data' or 'username' must be provided")

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token_payload(token: str) -> str:
    """Verify JWT token and return username."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# FastAPI dependency for extracting and verifying bearer token from Authorization header
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """FastAPI dependency that extracts and verifies JWT token from Authorization header."""
    return verify_token_payload(credentials.credentials)


# Database-based authentication
def authenticate_user(session, username: str, password: str) -> bool:
    """Authenticate user against database."""
    try:
        from store.user_models import User
        user = session.query(User).filter(User.username == username).first()
        if not user or not user.check_password(password):
            return False
        if not user.enabled:
            return False
        return True
    except Exception as e:
        logger.error(f"Auth error: {e}")
        return False


def get_current_user(session, token: str):
    """Get current user from token."""
    try:
        from store.user_models import User
        username = verify_token_payload(token)
        user = session.query(User).filter(User.username == username).first()
        if user is None or not user.enabled:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")


# User initialization
def bootstrap_roles_and_permissions(session) -> None:
    """Initialize default roles and permissions."""
    try:
        from store.user_models import Role, Permission

        # Define permissions
        permissions_data = [
            ("view_dashboard", "View the monitoring dashboard"),
            ("access_admin_page", "Access the chatbot admin configuration page"),
            ("change_password", "Change own password"),
            ("manage_users", "Create, read, update, delete users"),
            ("manage_roles", "Create, read, update, delete roles"),
        ]

        # Create permissions if they don't exist
        permissions = {}
        for perm_name, perm_desc in permissions_data:
            perm = session.query(Permission).filter(Permission.name == perm_name).first()
            if not perm:
                perm = Permission(name=perm_name, description=perm_desc)
                session.add(perm)
            permissions[perm_name] = perm

        session.commit()

        # Define roles with their permissions
        roles_data = {
            "dashboard": {
                "description": "Can view dashboard only",
                "permissions": ["view_dashboard", "change_password"],
            },
            "admin": {
                "description": "Can access dashboard and admin features",
                "permissions": ["view_dashboard", "access_admin_page", "change_password", "manage_users", "manage_roles"],
            },
        }

        # Create roles if they don't exist
        for role_name, role_info in roles_data.items():
            role = session.query(Role).filter(Role.name == role_name).first()
            if not role:
                role = Role(
                    name=role_name,
                    description=role_info["description"],
                    permissions=[permissions[perm] for perm in role_info["permissions"]],
                )
                session.add(role)

        session.commit()
        logger.info("Roles and permissions initialized")
    except Exception as e:
        logger.error(f"Error bootstrapping roles and permissions: {e}")


def bootstrap_default_user(session) -> None:
    """Create default admin user if no users exist."""
    try:
        from store.user_models import User, Role

        user_count = session.query(User).count()
        if user_count > 0:
            return

        # Create admin user
        admin_user = User(username="admin")
        admin_user.set_password("changeme")  # MUST be changed on first login!
        admin_role = session.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            admin_user.roles.append(admin_role)
        session.add(admin_user)
        session.commit()
        logger.warning("⚠️ Default admin user created with username='admin' and password='changeme'. CHANGE THIS IMMEDIATELY!")
    except Exception as e:
        logger.error(f"Error creating default user: {e}")
