from datetime import datetime
from uuid import UUID, uuid4

from pydantic import EmailStr, StrictStr
from sqlmodel import Field, SQLModel  # pyright: ignore[reportUnknownVariableType]


class StripeCustomer(SQLModel, table=True):
    """
    Model representing a media.

    Attributes:

    """

    __tablename__: str = "stripe_customer"  # pyright: ignore[reportIncompatibleVariableOverride]

    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    cus_id: StrictStr = Field(default=..., nullable=False, unique=True)
    guid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    invoice_prefix: StrictStr | None = Field(default=None, nullable=True)
    payment_method_id: StrictStr | None = Field(default=..., nullable=True, unique=True)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
    user_email: EmailStr = Field(foreign_key="user.email", nullable=False, unique=True)
    user_guid: UUID = Field(
        foreign_key="user.guid", nullable=False, index=True, unique=True
    )
