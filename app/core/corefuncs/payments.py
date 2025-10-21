from datetime import timedelta
from uuid import UUID

import stripe
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import Column

from app.api.exceptions.http_exc import APIException
from app.config import settings
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.enums.payee_account import CountryCode
from app.database.models.psql.payee_account import PayeeAccount
from app.database.models.psql.payment_intent import PaymentIntent
from app.database.models.psql.scheduled_payment import ScheduledPayment
from app.database.models.psql.stripe_customer import StripeCustomer
from app.database.models.psql.user import User
from app.datamodels.schemas.auth import FirebaseUser
from app.datamodels.schemas.request import ScheduledPaymentRequest
from app.datamodels.utils import to_stripe_amount_cents
from app.depends.depends import get_firebase_user

stripe.api_key = settings.STRIPE_SECRET_API_KEY


async def create_stripe_customer(
    db_session: PSQLSessionManager,
    user: User,
) -> StripeCustomer:
    # Create a new customer
    existing_customer: StripeCustomer | None = await db_session.find_one_or_none(
        model=StripeCustomer,
        criteria=(Column("user_guid") == user.guid,),
    )
    if existing_customer:
        raise APIException(api_context="user")
    customer: stripe.Customer = stripe.Customer.create(
        email=user.email,
        name=user.full_name,  # pyright: ignore[reportArgumentType] -> at this point in the flow `full_name` cannot be None
    )
    new_customer = StripeCustomer(
        invoice_prefix=customer.invoice_prefix,
        cus_id=customer.id,
        user_guid=user.guid,
        user_email=user.email,
    )
    await db_session.add(instance=new_customer)
    return new_customer


async def attach_payment_method(
    db_session: PSQLSessionManager,
    user: User,
    payment_method_id: str,
) -> StripeCustomer:
    # Attach the payment method
    customer: StripeCustomer | None = await db_session.find_one_or_none(
        model=StripeCustomer,
        criteria=(Column("user_guid") == user.guid,),
    )
    if not customer:
        raise APIException(api_context="user")
    pm: stripe.PaymentMethod = stripe.PaymentMethod.attach(
        payment_method_id,
        customer=customer.cus_id,
    )

    # Set as default payment method for invoices
    stripe.Customer.modify(
        customer.cus_id,
        invoice_settings={
            "default_payment_method": pm.id,
        },
    )
    customer.payment_method_id = pm.id
    return customer


async def schedule_payment_intent(
    db_session: PSQLSessionManager,
    user: User,
    event_guid: UUID,
    payload: ScheduledPaymentRequest,
) -> ScheduledPayment:
    # Attach the payment method
    customer: StripeCustomer | None = await db_session.find_one_or_none(
        model=StripeCustomer,
        criteria=(Column("user_guid") == user.guid,),
    )
    if not customer or not customer.payment_method_id:
        raise APIException(api_context="user")
    scheduled_payment: ScheduledPayment = ScheduledPayment(
        due_date=payload.event_date.date()
        - timedelta(days=2),  # payment scheduled 2 days before event date
        stripe_customer_guid=customer.guid,
        amount_cents=to_stripe_amount_cents(
            amount=payload.amount,
            currency=payload.currency,
        ),
        currency=payload.currency,
        stripe_payee_account_guid=payload.paye_account_guid,
        event_guid=event_guid,
    )
    await db_session.add(scheduled_payment)
    return scheduled_payment


async def make_scheduled_payment(
    db_session: PSQLSessionManager,
    scheduled_payment_guid: UUID,
    customer_guid: UUID,
) -> ScheduledPayment:
    # Attach the payment method
    scheduled_payment: ScheduledPayment | None = await db_session.find_one_or_none(
        model=ScheduledPayment,
        criteria=(Column("guid") == scheduled_payment_guid,),
    )
    if not scheduled_payment:
        raise APIException(api_context="user")
    if scheduled_payment.discharged:
        raise APIException(api_context="user")
    customer: StripeCustomer | None = await db_session.find_one_or_none(
        model=StripeCustomer,
        criteria=(Column("guid") == customer_guid,),
    )
    if not customer or not customer.payment_method_id:
        raise APIException(api_context="user")
    payee: PayeeAccount | None = await db_session.find_one_or_none(
        model=PayeeAccount,
        criteria=(Column("guid") == scheduled_payment.stripe_payee_account_guid,),
    )
    if not payee or not customer.payment_method_id:
        raise APIException(api_context="user")

    intent: stripe.PaymentIntent = stripe.PaymentIntent.create(
        amount=scheduled_payment.amount_cents,
        currency=scheduled_payment.currency.value,
        customer=customer.cus_id,
        payment_method=customer.payment_method_id,
        application_fee_amount=int(
            scheduled_payment.amount_cents * settings.APP_PERC_FEE
        ),
        off_session=True,  # Charge without user interaction
        confirm=True,
        transfer_data={
            "destination": payee.account_id,
        },
    )
    scheduled_payment.discharged = True
    payment_intent = PaymentIntent(
        payment_intent_id=intent.id,
        status=intent.status,
        stripe_customer_guid=customer.guid,
        app_fee_amount=intent.application_fee_amount,
    )
    await db_session.add(payment_intent)
    return scheduled_payment


async def create_stripe_payee_account(
    country_code: CountryCode,
    request: Request,
) -> str:
    auth_creds: str = request.headers.get("authorization", "")
    token: str = auth_creds.split("Bearer")[-1].lstrip()
    account: stripe.Account = stripe.Account.create(
        type="express",
        country=country_code.value,
        capabilities={
            "transfers": {
                "requested": True,
            },
            "card_payments": {
                "requested": True,
            },
        },
        business_type="individual",
    )
    account_link: stripe.AccountLink = stripe.AccountLink.create(
        account=account.id,
        refresh_url=f"{request.base_url!s}payments/users/me/profile&token={token}",
        return_url=f"{request.base_url!s}payments/payee-account/onboarding-complete?token={token}&spaccount_id={account.id}",
        type="account_onboarding",
    )
    return account_link.url


async def complete_payee_account_onboarding(
    db_session: PSQLSessionManager,
    spaccount_id: str,
    token: str,
) -> PayeeAccount:
    # stripe.Account.delete("acct_1SKISG2dfKZNjS3i")
    firebase_user: FirebaseUser = await get_firebase_user(
        authcreds=HTTPAuthorizationCredentials(
            credentials=token,
            scheme="Bearer",
        ),
    )
    psql_user: User | None = await db_session.find_one_or_none(
        model=User, criteria=(Column("email") == firebase_user.email,)
    )
    if not psql_user:
        raise APIException("auth")

    stripe_payee: stripe.Account = stripe.Account.retrieve(id=spaccount_id)  # pyright: ignore[reportUnknownMemberType]
    new_payee = PayeeAccount(
        account_id=spaccount_id,
        user_guid=psql_user.guid,
        country_code=CountryCode(stripe_payee.country),
    )
    await db_session.add(new_payee)
    return new_payee
