from datetime import datetime
from uuid import UUID, uuid4

from pydantic import StrictStr
from sqlmodel import Field, SQLModel

from app.database.models.enums.payee_account import CountryCode


class PayeeAccount(SQLModel, table=True):
    """
    Model representing a media.

    Attributes:

    """

    __tablename__: str = "payee_account"

    account_id: StrictStr = Field(default=..., nullable=False, unique=True)
    country_code: CountryCode = Field(default=..., nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    guid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
    user_guid: UUID = Field(
        foreign_key="user.guid", nullable=False, index=True, unique=True
    )
