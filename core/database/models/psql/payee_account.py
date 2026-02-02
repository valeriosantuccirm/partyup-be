from datetime import datetime
from uuid import UUID, uuid4

from pydantic import StrictStr
from sqlmodel import Field, SQLModel  # pyright: ignore[reportUnknownVariableType]

from core.database.models.enums.payee_account import CountryCode, PayeeAccountStatus


class PayeeAccount(SQLModel, table=True):
    """
    Model representing a media.

    Attributes:

    """

    __tablename__: str = "payee_account"  # pyright: ignore[reportIncompatibleVariableOverride]

    account_id: StrictStr | None = Field(default=None, nullable=True, unique=True)
    country_code: CountryCode | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    guid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    status: PayeeAccountStatus = Field(
        default=PayeeAccountStatus.PENDING, nullable=False
    )
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
    user_guid: UUID = Field(
        foreign_key="user.guid", nullable=False, index=True, unique=True
    )
