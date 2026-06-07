"""User management models with role-based access control."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Table, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from store import Base

# Association tables for many-to-many relationships
user_roles_association = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('role.id'), primary_key=True),
)

role_permissions_association = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('role.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permission.id'), primary_key=True),
)


class Permission(Base):
    """Permission model for fine-grained access control."""
    __tablename__ = 'permission'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String(512))

    roles = relationship('Role', secondary=role_permissions_association, back_populates='permissions')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
        }


class Role(Base):
    """Role model for grouping permissions."""
    __tablename__ = 'role'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String(512))

    permissions = relationship('Permission', secondary=role_permissions_association, back_populates='roles')
    users = relationship('User', secondary=user_roles_association, back_populates='roles')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'permissions': [p.to_dict() for p in self.permissions],
        }

    def has_permission(self, permission_name: str) -> bool:
        """Check if role has a specific permission."""
        return any(p.name == permission_name for p in self.permissions)


class UserProfile(Base):
    """User profile for storing additional user data."""
    __tablename__ = 'user_profile'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), unique=True, nullable=False)
    profile_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', back_populates='profile')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'profile_data': self.profile_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class User(Base):
    """User model with password hashing and role management."""
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roles = relationship('Role', secondary=user_roles_association, back_populates='users')
    profile = relationship('UserProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password: str):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission through any of their roles."""
        return any(role.has_permission(permission_name) for role in self.roles)

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return any(role.name == role_name for role in self.roles)

    def to_dict(self, include_password=False):
        """Convert user to dictionary."""
        data = {
            'id': self.id,
            'username': self.username,
            'enabled': self.enabled,
            'roles': [role.to_dict() for role in self.roles],
            'permissions': list(set(
                p.name for role in self.roles for p in role.permissions
            )),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_password:
            data['password_hash'] = self.password_hash
        return data
