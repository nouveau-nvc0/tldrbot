"""Optional analytics storage."""
from datetime import datetime
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import create_engine, Column, Integer, BigInteger, String, DateTime, Text, text
    from sqlalchemy.orm import declarative_base, sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

_engine = None
_SessionLocal = None

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()

    class UserEvent(Base):
        __tablename__ = "user_events"

        id = Column(Integer, primary_key=True, autoincrement=True)
        user_id = Column(BigInteger, nullable=False)
        username = Column(String(64), nullable=True)
        chat_id = Column(BigInteger, nullable=False)
        event_type = Column(String(64), nullable=False)
        timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
        extra = Column(Text, nullable=True)
else:
    Base = None
    UserEvent = None


def _ensure_sqlite_directory(database_url: str) -> None:
    if not database_url.startswith("sqlite:///") or database_url == "sqlite:///:memory:":
        return

    path = database_url.removeprefix("sqlite:///")
    if not path:
        return

    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)


def init_database(database_url: str | None, create_schema: bool = True) -> bool:
    global _engine, _SessionLocal
    if not SQLALCHEMY_AVAILABLE or not database_url:
        return False

    try:
        _ensure_sqlite_directory(database_url)
        _engine = create_engine(database_url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)

        with _engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        if create_schema:
            create_tables()
        return True
    except Exception as e:
        logger.error(f"Failed to init database: {e}")
        _engine = None
        _SessionLocal = None
        return False


def create_tables() -> None:
    if Base and _engine:
        Base.metadata.create_all(bind=_engine)


def log_event(user_id: int, chat_id: int, event_type: str, username: Optional[str] = None, extra: Optional[str] = None) -> None:
    if not _SessionLocal:
        return
    if not UserEvent:
        return

    session = _SessionLocal()
    try:
        session.add(UserEvent(user_id=user_id, chat_id=chat_id, event_type=event_type, username=username, extra=extra))
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"Failed to log analytics event: {e}")
    finally:
        session.close()

