import asyncio
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import Column

from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.psql.scheduled_payment import ScheduledPayment
from app.database.session import psql_session_manager_sync
from pubsub_workers.payments.src.schema.qr_data import QRData
from pubsub_workers.payments.src.services import make_payment, send_qrcode


# Async logic for processing a message
async def process_daily_pending_payments() -> None:
    try:
        session: PSQLSessionManager | None = psql_session_manager_sync()
        if session:
            due_payments: Sequence[ScheduledPayment] = await session.get(
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


if __name__ == "__main__":
    asyncio.run(process_daily_pending_payments())
