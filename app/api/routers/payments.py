from typing import Annotated, Any
from uuid import UUID

import stripe
from fastapi import APIRouter, Body, Depends, Path, Query, Request
from starlette import status

from app.core.corefuncs import payments
from app.core.decorators import manage_transaction
from app.database.crud.psql.psqlclient import PSQLClient
from app.database.models.enums.payee_account import PayeeAccountStatus
from app.database.models.psql.payee_account import PayeeAccount
from app.database.models.psql.scheduled_payment import ScheduledPayment
from app.database.models.psql.stripe_customer import StripeCustomer
from app.database.models.psql.user import User
from app.database.session import psqlclient
from app.datamodels.schemas.request import (
    OnboardingRequestBody,
    ScheduledPaymentRequest,
)
from app.depends.depends import admit_user

router = APIRouter(prefix="/payments")


@router.post(
    path="/customer",
    response_model=StripeCustomer,
    status_code=status.HTTP_201_CREATED,
)
@manage_transaction
async def create_customer(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
) -> StripeCustomer:
    """ """
    return await payments.create_stripe_customer(
        db_session=db_session,
        user=user,
    )


@router.patch(
    path="/payment-method/attach",
    response_model=StripeCustomer,
    status_code=status.HTTP_200_OK,
)
@manage_transaction
async def attach_payment_method_to_user(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
    payment_method_id: Annotated[str, Body(default=...)],
) -> StripeCustomer:
    """ """
    return await payments.attach_payment_method(
        db_session=db_session,
        user=user,
        payment_method_id=payment_method_id,
    )


@router.post(
    path="/{event_guid}/schedule",
    response_model=ScheduledPayment,
    status_code=status.HTTP_201_CREATED,
)
@manage_transaction
async def schedule_payment_intent(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
    event_guid: Annotated[UUID, Path(default=...)],
    payload: Annotated[ScheduledPaymentRequest, Body(default=...)],
) -> ScheduledPayment:
    """ """
    return await payments.schedule_payment_intent(
        db_session=db_session,
        user=user,
        event_guid=event_guid,
        payload=payload,
    )


@router.put(
    path="/{scheduled_payment_guid}/customers/{customer_guid}/make",
    response_model=ScheduledPayment,
    status_code=status.HTTP_201_CREATED,
)
@manage_transaction
async def make_payment(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    _: Annotated[User, Depends(dependency=admit_user)],
    scheduled_payment_guid: Annotated[UUID, Path(default=...)],
    customer_guid: Annotated[UUID, Path(default=...)],
) -> ScheduledPayment:
    """ """
    return await payments.make_scheduled_payment(
        db_session=db_session,
        scheduled_payment_guid=scheduled_payment_guid,
        customer_guid=customer_guid,
    )


@router.post(
    path="/payee-account/onboarding",
    status_code=status.HTTP_201_CREATED,
)
@manage_transaction
async def create_payee_account(
    request: Annotated[Request, Any],  # TODO: for test
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
    payload: Annotated[OnboardingRequestBody, Body(default=...)],
) -> str:
    """ """
    return await payments.create_stripe_payee_account(
        db_session=db_session,
        user=user,
        country_code=payload.country_code,
        request=request,
    )


@router.get(
    path="/payee-account/onboarding/return-url-callback",
    status_code=status.HTTP_200_OK,
)
@manage_transaction
async def get_stripe_return_url(
    request: Annotated[Request, Any],  # TODO: for test
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    token: Annotated[str, Query(default=...)],
) -> str:
    """ """
    return await payments.get_stripe_customer_refresh_link(
        db_session=db_session,
        request=request,
        auth_token=token,
    )


@router.get(
    path="/payee-account/onboarding-complete",
    response_model=PayeeAccount,
    status_code=status.HTTP_201_CREATED,
)
@manage_transaction
async def confirm_payee_account_creation(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
    spaccount_id: Annotated[str, Query(default=...)],
) -> PayeeAccount:
    """ """
    return await payments.complete_payee_account_onboarding(
        db_session=db_session,
        user=user,
        spaccount_id=spaccount_id,
    )


@router.get(
    path="/account-status",
    status_code=status.HTTP_201_CREATED,
)
@manage_transaction
async def check_payee_account_status(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
) -> PayeeAccountStatus:
    """ """
    return await payments.get_payee_account_status(
        db_session=db_session,
        user=user,
    )


@router.get(
    path="/payees/me/account",
    status_code=status.HTTP_200_OK,
)
@manage_transaction
async def get_payee_account_card(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
) -> PayeeAccount:
    """ """
    return await payments.get_payee_account(
        db_session=db_session,
        user=user,
    )


@router.get(
    path="/customers/me",
    status_code=status.HTTP_200_OK,
)
@manage_transaction
async def get_customer_account_card(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
) -> StripeCustomer:
    """ """
    return await payments.get_customer(
        db_session=db_session,
        user=user,
    )


@router.post(
    path="/customers/me/setup-intent",
    status_code=status.HTTP_201_CREATED,
)
@manage_transaction
async def create_setup_intent(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
) -> Any:
    customer: StripeCustomer = await payments.get_customer(
        db_session=db_session,
        user=user,
    )
    setup_intent: stripe.SetupIntent = stripe.SetupIntent.create(
        customer=customer.cus_id,
        payment_method_types=["card"],
        usage="off_session",
    )
    return {
        "client_secret": setup_intent.client_secret,
    }


@router.post(
    path="/customers/me/confirm-payment-method",
    status_code=status.HTTP_200_OK,
)
@manage_transaction
async def confirm_payment_method(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
    payload: Annotated[dict[str, str], Body(default=...)],
) -> StripeCustomer:
    customer: StripeCustomer = await payments.get_customer(
        db_session=db_session,
        user=user,
    )
    stripe.Customer.modify(
        customer.cus_id,
        invoice_settings={
            "default_payment_method": payload["payment_method"],
        },
    )
    customer.payment_method_id = payload["payment_method"]
    return customer
