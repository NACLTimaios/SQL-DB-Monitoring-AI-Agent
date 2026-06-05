"""Storage layer: engine factory, session factory, and health check."""

import logging
from typing import Callable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from store.models import Base

logger = logging.getLogger(__name__)


def get_engine(database_url: str) -> Engine:
    """Create and return a SQLAlchemy engine for *database_url*.

    Pool settings are tuned for the ARM64 2-OCPU / 12 GB target.
    """
    engine = create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )
    logger.info("Engine created for %s", _redact(database_url))
    return engine


def init_db(engine: Engine) -> None:
    """Create all tables declared on ``Base`` if they do not exist."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialised")


def get_session(engine: Engine) -> Callable[[], Session]:
    """Return a session factory bound to *engine*.

    Usage::

        factory = get_session(engine)
        session = factory()
        try:
            ...
        finally:
            session.close()
    """
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return factory


def check_db_health(engine: Engine) -> bool:
    """Return True if the database is reachable and responsive."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return False


def _redact(url: str) -> str:
    """Replace password in URL with *** for safe logging."""
    import re
    return re.sub(r"(://[^:]+:)[^@]+(@)", r"\1***\2", url)
