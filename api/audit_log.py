"""Audit logging for security-sensitive operations."""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Request


def setup_audit_logger() -> logging.Logger:
    """Set up separate audit logger with restricted file permissions."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    audit_log_path = log_dir / "audit.log"

    # Create logger
    logger = logging.getLogger("audit")
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create file handler with restricted permissions
    handler = logging.FileHandler(audit_log_path)
    handler.setLevel(logging.INFO)

    # Set file permissions to 600 (user read/write only)
    os.chmod(audit_log_path, 0o600)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


# Initialize audit logger
audit_logger = setup_audit_logger()


def log_login_attempt(username: str, success: bool, ip_address: str, error_msg: Optional[str] = None) -> None:
    """Log login attempt."""
    status = "SUCCESS" if success else "FAILED"
    msg = f"LOGIN | {status} | username={username} | ip={ip_address}"
    if error_msg:
        msg += f" | error={error_msg}"
    audit_logger.info(msg)


def log_user_creation(admin_username: str, new_username: str, role: str, ip_address: str) -> None:
    """Log user creation."""
    msg = f"USER_CREATED | username={new_username} | role={role} | created_by={admin_username} | ip={ip_address}"
    audit_logger.info(msg)


def log_password_change(username: str, changed_by: str, ip_address: str) -> None:
    """Log password change."""
    msg = f"PASSWORD_CHANGED | username={username} | changed_by={changed_by} | ip={ip_address}"
    audit_logger.info(msg)


def log_user_deletion(deleted_username: str, deleted_by: str, ip_address: str) -> None:
    """Log user deletion."""
    msg = f"USER_DELETED | username={deleted_username} | deleted_by={deleted_by} | ip={ip_address}"
    audit_logger.info(msg)


def log_user_update(updated_username: str, updated_by: str, changes: dict, ip_address: str) -> None:
    """Log user update."""
    changes_str = ", ".join([f"{k}={v}" for k, v in changes.items()])
    msg = f"USER_UPDATED | username={updated_username} | updated_by={updated_by} | changes={changes_str} | ip={ip_address}"
    audit_logger.info(msg)


def log_admin_config_change(admin_username: str, config_key: str, old_value: str, new_value: str, ip_address: str) -> None:
    """Log admin configuration changes."""
    msg = f"CONFIG_CHANGED | key={config_key} | old_value={old_value} | new_value={new_value} | changed_by={admin_username} | ip={ip_address}"
    audit_logger.info(msg)


def get_client_ip_from_request(request: Request) -> str:
    """Extract client IP from request, accounting for proxies."""
    if request.headers.get("x-forwarded-for"):
        return request.headers.get("x-forwarded-for").split(",")[0].strip()
    return request.client.host if request.client else "unknown"
