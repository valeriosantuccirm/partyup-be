from datetime import datetime
from uuid import UUID, uuid4

from pydantic import StrictFloat, StrictStr
from sqlmodel import Field, SQLModel  # pyright: ignore[reportUnknownVariableType]


class PaymentIntent(SQLModel, table=True):
    """
    Model representing a media.

    Attributes:

    """

    __tablename__: str = "payment_intent"  # pyright: ignore[reportIncompatibleVariableOverride]

    app_fee_amount: StrictFloat | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    guid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    payment_intent_id: StrictStr | None = Field(default=..., nullable=True, unique=True)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
    status: StrictStr = Field(default=..., nullable=False)
    stripe_customer_guid: UUID = Field(
        foreign_key="stripe_customer.guid", nullable=False, index=True
    )
