from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

from backend.app.models.organization import Organization