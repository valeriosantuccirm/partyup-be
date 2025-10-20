import asyncio
from collections.abc import Sequence
from datetime import date
from typing import Any

import stripe
from sqlalchemy import Column

from app.config import settings
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.psql.payee_account import PayeeAccount
from app.database.models.psql.payment_intent import PaymentIntent
from app.database.models.psql.scheduled_payment import ScheduledPayment
from app.database.models.psql.stripe_customer import StripeCustomer
from app.database.session import psql_session_manager_sync


async def _make_payment(
    scheduled_payment: ScheduledPayment,
) -> ScheduledPayment | None:
    session: PSQLSessionManager | None = psql_session_manager_sync()
    if session:
        payee_account: PayeeAccount | None = await session.find_one_or_none(
            model=PayeeAccount,
            criteria=(Column("guid") == scheduled_payment.stripe_payee_account_guid,),
        )
        if not payee_account:
            raise Exception

        customer: StripeCustomer | None = await session.find_one_or_none(
            model=StripeCustomer,
            criteria=(Column("guid") == scheduled_payment.stripe_payee_account_guid,),
        )
        if not customer:
            raise Exception

        if not customer.payment_method_id:
            raise Exception

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
                "destination": payee_account.account_id,
            },
        )
        scheduled_payment.discharged = True
        payment_intent = PaymentIntent(
            payment_intent_id=intent.id,
            status=intent.status,
            stripe_customer_guid=customer.guid,
            app_fee_amount=intent.application_fee_amount,
        )
        await session.add(payment_intent)
        return scheduled_payment


# Async logic for processing a message
async def process_daily_pending_payments() -> None:
    session: PSQLSessionManager | None = psql_session_manager_sync()
    if session:
        due_payments: Sequence[ScheduledPayment] = await session.get(
            model=ScheduledPayment,
            criteria=(
                Column("due_date") == date.today(),
                Column("discharged").is_(False),
            ),
        )
        tasks: list[Any] = []
        for due_payment in due_payments:
            loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
            tasks.append(
                loop.create_task(
                    _make_payment(
                        scheduled_payment=due_payment,
                    ),
                )
            )
        processed: list[ScheduledPayment | None] = await asyncio.gather(**tasks)


if __name__ == "__main__":
    asyncio.run(process_daily_pending_payments())
