from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, StrictFloat, StrictStr, field_serializer


class BaseQRCodeData(BaseModel):
    name: StrictStr | None = Field(default=None)
    guid: UUID = Field(default=...)

    @field_serializer("guid")
    def _tostr(self, value: UUID) -> str:
        return str(value)


class BaseQRCodePaymentData(BaseModel):
    status: StrictStr = Field(default=...)
    amount: StrictFloat = Field(default=...)
    currency: StrictStr = Field(default=...)
    timestamp: date = Field(default=...)

    @field_serializer("timestamp")
    def _tostr(self, value: date) -> str:
        return value.isoformat()


class QRData(BaseModel):
    event: BaseQRCodeData = Field(default=...)
    attendee: BaseQRCodeData = Field(default=...)
    creator: BaseQRCodeData = Field(default=...)
    payment: BaseQRCodePaymentData = Field(default=...)
