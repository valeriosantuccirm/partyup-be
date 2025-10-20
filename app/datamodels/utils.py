from decimal import ROUND_HALF_UP, Decimal

from starlette import status
from starlette.datastructures import UploadFile as starletteUploadFile

from app.api.exceptions.http_exc import APIException
from app.constants import USER_API_CONTEXT
from app.database.models.enums.scheduled_payment import Currency


def validate_fileimage_extension(
    value: starletteUploadFile | None,
) -> starletteUploadFile | None:
    if isinstance(value, starletteUploadFile):
        if value.content_type not in ("image/jpg", "image/png", "image/jpeg"):
            raise APIException(
                api_context=USER_API_CONTEXT,
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only 'PNG' and 'JPEG' format are allowed",
            )
        return value
    return value


def to_stripe_amount_cents(
    amount: float | str | Decimal,
    currency: Currency = Currency.eur,
) -> int:
    """
    Convert a monetary amount to the smallest unit (like cents) for Stripe.
    """
    ZERO_DECIMAL_CURRENCIES: set[str] = {"jpy", "krw"}

    amount = Decimal(str(amount))  # Ensures safe conversion
    if currency.value.lower() in ZERO_DECIMAL_CURRENCIES:
        return int(amount.to_integral_value(rounding=ROUND_HALF_UP))
    return int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))
