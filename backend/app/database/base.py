from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """Current UTC time as a naive datetime.

    The existing tables use timezone-naive DateTime columns that hold UTC, so
    values are written the same way (datetime.utcnow() is deprecated).
    """
    return datetime.now(UTC).replace(tzinfo=None)
