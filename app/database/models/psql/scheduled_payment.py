from datetime import date, datetime
from uuid import UUID, uuid4

from pydantic import StrictBool, StrictInt
from sqlmodel import Field, SQLModel

from app.database.models.enums.scheduled_payment import Currency


class ScheduledPayment(SQLModel, table=True):
    """
    Model representing a media.

    Attributes:

    """

    __tablename__: str = "scheduled_payment"

    amount_cents: StrictInt = Field(default=..., nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    currency: Currency = Field(default=..., nullable=False)
    discharged: StrictBool = Field(default=False, nullable=False)
    due_date: date = Field(default=..., nullable=False)
    guid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
    stripe_customer_guid: UUID = Field(
        foreign_key="stripe_customer.guid", nullable=False, index=True
    )
    stripe_payee_account_guid: UUID = Field(
        foreign_key="payee_account.guid", nullable=False, index=True
    )
