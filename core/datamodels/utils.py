from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException
from starlette import status
from starlette.datastructures import UploadFile as starletteUploadFile

from core.database.models.enums.scheduled_payment import Currency


def validate_fileimage_extension(
    value: starletteUploadFile | None,
) -> starletteUploadFile | None:
    if isinstance(value, starletteUploadFile):
        if value.content_type not in ("image/jpg", "image/png", "image/jpeg"):
            raise HTTPException(
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


def from_stripe_amount_cents(
    amount_cents: int,
    currency: Currency = Currency.eur,
) -> Decimal:
    """
    Convert Stripe's integer amount (in smallest unit) back to a normal decimal amount.
    """
    ZERO_DECIMAL_CURRENCIES: set[str] = {"jpy", "krw"}

    if currency.value.lower() in ZERO_DECIMAL_CURRENCIES:
        # No fractional part — 100 JPY = 100 (no cents)
        return Decimal(amount_cents).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    else:
        # Convert cents to decimal currency (e.g., 1099 → 10.99)
        return (Decimal(amount_cents) / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
