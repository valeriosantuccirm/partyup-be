from datetime import timedelta
from uuid import UUID

import stripe
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import Column
from starlette import status

from app.depends.depends import get_firebase_user
from core.config import settings
from core.database.crud.psql.psqlclient import PSQLClient
from core.database.models.enums.payee_account import CountryCode, PayeeAccountStatus
from core.database.models.psql.payee_account import PayeeAccount
from core.database.models.psql.payment_intent import PaymentIntent
from core.database.models.psql.scheduled_payment import ScheduledPayment
from core.database.models.psql.stripe_customer import StripeCustomer
from core.database.models.psql.user import User
from core.datamodels.schemas.auth import FirebaseUser
from core.datamodels.schemas.request import ScheduledPaymentRequest
from core.datamodels.utils import to_stripe_amount_cents


async def create_stripe_customer(
    db_session: PSQLClient,
    user: User,
) -> StripeCustomer:
    # Create a new customer
    existing_customer: StripeCustomer | None = await db_session.find_one_or_none(
        model=StripeCustomer,
        criteria=(Column("user_guid") == user.guid,),
    )
    if existing_customer:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer already exists",
        )
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
    db_session: PSQLClient,
    user: User,
    payment_method_id: str,
) -> StripeCustomer:
    # Attach the payment method
    customer: StripeCustomer | None = await db_session.find_one_or_none(
        model=StripeCustomer,
        criteria=(Column("user_guid") == user.guid,),
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
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
    db_session: PSQLClient,
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    scheduled_payment: ScheduledPayment = ScheduledPayment(
        due_date=payload.event_date.date()
        - timedelta(days=2),  # payment scheduled 2 days before event date
        stripe_customer_guid=customer.guid,
        amount_cents=to_stripe_amount_cents(
            amount=payload.amount,
            currency=payload.currency,
        ),
        currency=payload.currency,
        stripe_payee_account_guid=payload.payee_account_guid,
        event_guid=event_guid,
    )
    await db_session.add(scheduled_payment)
    return scheduled_payment


async def make_scheduled_payment(
    db_session: PSQLClient,
    scheduled_payment_guid: UUID,
    customer_guid: UUID,
) -> ScheduledPayment:
    # Attach the payment method
    scheduled_payment: ScheduledPayment | None = await db_session.find_one_or_none(
        model=ScheduledPayment,
        criteria=(Column("guid") == scheduled_payment_guid,),
    )
    if not scheduled_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scheduled payment found",
        )
    if scheduled_payment.discharged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already processed",
        )
    customer: StripeCustomer | None = await db_session.find_one_or_none(
        model=StripeCustomer,
        criteria=(Column("guid") == customer_guid,),
    )
    if not customer or not customer.payment_method_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    payee: PayeeAccount | None = await db_session.find_one_or_none(
        model=PayeeAccount,
        criteria=(Column("guid") == scheduled_payment.stripe_payee_account_guid,),
    )
    if not payee or not customer.payment_method_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payee not found",
        )

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
    db_session: PSQLClient,
    user: User,
    country_code: CountryCode,
    request: Request,
) -> str:
    auth_creds: str = request.headers.get("authorization", "")
    token: str = auth_creds.split("Bearer")[-1].lstrip()
    customer: PayeeAccount | None = await db_session.find_one_or_none(
        model=PayeeAccount, criteria=(Column("user_guid") == user.guid,)
    )
    if customer and customer.status == PayeeAccountStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    if customer:
        account: stripe.Account = stripe.Account.retrieve(id=customer.account_id)  # pyright: ignore[reportUnknownMemberType]
    else:
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
        refresh_url=f"{request.base_url!s}payments/payee-account/onboarding/return-url-callback?token={token}",
        return_url=f"{request.base_url!s}users/me/profile",
        type="account_onboarding",
    )
    if not customer:
        await db_session.add(
            instance=PayeeAccount(
                user_guid=user.guid,
                account_id=account.id,
            )
        )
    return account_link.url


async def get_stripe_customer_refresh_link(
    db_session: PSQLClient,
    request: Request,
    auth_token: str,
) -> str:
    firebase_user: FirebaseUser = await get_firebase_user(
        authcreds=HTTPAuthorizationCredentials(
            credentials=auth_token,
            scheme="Bearer",
        ),
    )
    psql_user: User | None = await db_session.find_one_or_none(
        model=User, criteria=(Column("email") == firebase_user.email,)
    )
    if not psql_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    customer: PayeeAccount | None = await db_session.find_one_or_none(
        model=PayeeAccount, criteria=(Column("user_guid") == psql_user.guid,)
    )
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    account: stripe.Account = stripe.Account.retrieve(id=customer.account_id)  # pyright: ignore[reportUnknownMemberType]
    account_link: stripe.AccountLink = stripe.AccountLink.create(
        account=account.id,
        refresh_url=f"{request.base_url!s}payments/payee-account/onboarding/return-url-callback?token={auth_token}",
        return_url=f"{request.base_url!s}users/me/profile",
        type="account_onboarding",
    )
    customer.country_code = CountryCode(account.country)
    acc_status = PayeeAccountStatus.PENDING
    customer.status = (
        PayeeAccountStatus.ACTIVE
        if account.charges_enabled and account.payouts_enabled
        else acc_status
    )
    return (
        account_link.url
    )  # TODO: when refreshing i need on FE to redirect the returned account link


async def complete_payee_account_onboarding(
    db_session: PSQLClient,
    user: User,
    spaccount_id: str,
) -> PayeeAccount:
    payee_account: PayeeAccount | None = await db_session.find_one_or_none(
        model=PayeeAccount, criteria=(Column("user_guid") == user.guid,)
    )
    if not payee_account:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    stripe_payee: stripe.Account = stripe.Account.retrieve(id=spaccount_id)  # pyright: ignore[reportUnknownMemberType]
    payee_account.account_id = stripe_payee.id
    payee_account.country_code = CountryCode(stripe_payee.country)
    payee_account.status = PayeeAccountStatus.ACTIVE
    return payee_account


async def get_payee_account_status(
    db_session: PSQLClient,
    user: User,
) -> PayeeAccountStatus:
    payee_account: PayeeAccount | None = await db_session.find_one_or_none(
        model=PayeeAccount, criteria=(Column("user_guid") == user.guid,)
    )
    if not payee_account:
        return PayeeAccountStatus.NOT_CONNECTED
    return payee_account.status


async def get_payee_account(
    db_session: PSQLClient,
    user: User,
) -> PayeeAccount:
    payee_account: PayeeAccount | None = await db_session.find_one_or_none(
        model=PayeeAccount, criteria=(Column("user_guid") == user.guid,)
    )
    if not payee_account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return payee_account


async def get_customer(
    db_session: PSQLClient,
    user: User,
) -> StripeCustomer:
    stripe_customer: StripeCustomer | None = await db_session.find_one_or_none(
        model=StripeCustomer, criteria=(Column("user_guid") == user.guid,)
    )
    if not stripe_customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return stripe_customer
