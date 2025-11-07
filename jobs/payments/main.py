import asyncio
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import Column

from app.database.crud.psql.psqlclient import PSQLClient
from app.database.models.psql.scheduled_payment import ScheduledPayment
from app.database.session import psqlclient
from jobs.payments.src.schema.qr_data import QRData
from jobs.payments.src.services import make_payment, send_qrcode


async def process_daily_pending_payments() -> None:
    try:
        session: PSQLClient = await anext(psqlclient())
        due_payments: Sequence[ScheduledPayment] = await session.get_all(
            model=ScheduledPayment,
            criteria=(
                Column("due_date") == date.today(),
                Column("discharged").is_(False),
                Column("amount_cents") > 0,
            ),
        )

        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        payment_tasks: list[Any] = []
        for due_payment in due_payments:
            payment_tasks.append(
                loop.create_task(
                    make_payment(
                        scheduled_payment=due_payment,
                    ),
                )
            )
        qrdata_list: list[QRData | BaseException] = await asyncio.gather(
            *payment_tasks,
            return_exceptions=True,
        )

        qrcode_notification_tasks: list[Any] = []
        for qrdata in qrdata_list:
            if isinstance(qrdata, QRData):
                qrcode_notification_tasks.append(
                    loop.create_task(
                        send_qrcode(
                            qrdata=qrdata,
                        ),
                    )
                )
        await asyncio.gather(
            *qrcode_notification_tasks,
            return_exceptions=True,
        )
    except Exception as e:
        raise e
