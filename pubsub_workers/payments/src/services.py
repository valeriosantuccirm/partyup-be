from datetime import datetime, timedelta
from uuid import uuid4

import stripe
from google.cloud.storage import (  # pyright: ignore[reportMissingTypeStubs]
    Bucket,
    Client,
)
from google.cloud.storage.blob import Blob  # pyright: ignore[reportMissingTypeStubs]
from sqlalchemy import Column

from app.config import settings
from app.core import fcm
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.psql.event import Event
from app.database.models.psql.payee_account import PayeeAccount
from app.database.models.psql.payment_intent import PaymentIntent
from app.database.models.psql.qr_ticket import QRTicket
from app.database.models.psql.scheduled_payment import ScheduledPayment
from app.database.models.psql.stripe_customer import StripeCustomer
from app.database.models.psql.user import User
from app.database.session import psql_session_manager_sync
from app.datamodels.utils import from_stripe_amount_cents
from pubsub_workers.payments.src.qrcode.generator import (
    create_partyup_ticket,
)
from pubsub_workers.payments.src.schema.qr_data import (
    BaseQRCodeData,
    BaseQRCodePaymentData,
    QRData,
)


async def make_payment(
    scheduled_payment: ScheduledPayment,
) -> QRData | None:
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

        event: Event | None = await session.find_one_or_none(
            model=Event,
            criteria=(Column("event_guid") == scheduled_payment.event_guid,),
        )
        if not event:
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
        scheduled_payment.updated_at = datetime.now()
        payment_intent = PaymentIntent(
            payment_intent_id=intent.id,
            status=intent.status,
            stripe_customer_guid=customer.guid,
            app_fee_amount=intent.application_fee_amount,
        )
        await session.add(payment_intent)

        return QRData(
            event=BaseQRCodeData(
                name=event.title,
                guid=event.guid,
            ),
            attendee=BaseQRCodeData(
                name=customer.user_email,
                guid=customer.user_guid,
            ),
            creator=BaseQRCodeData(
                guid=payee_account.user_guid,
            ),
            payment=BaseQRCodePaymentData(
                status=intent.status,
                amount=float(
                    float(
                        from_stripe_amount_cents(
                            scheduled_payment.amount_cents,
                        ),
                    )
                ),
                currency=intent.currency,
                timestamp=scheduled_payment.due_date,
            ),
        )


async def send_qrcode(
    qrdata: QRData,
) -> None:
    session: PSQLSessionManager | None = psql_session_manager_sync()
    if session:
        qr_code: bytes = await create_partyup_ticket(
            qrdata=qrdata,
        )

        # TODO: save ticket img in GCP and return url
        ticket_url: str = await upload_ticket_to_gcs(
            image_bytes=qr_code,
            bucket_name="",
            event_title=qrdata.event.name,
        )

        new_ticket = QRTicket(
            attendee_guid=qrdata.attendee.guid,
            event_guid=qrdata.event.guid,
            qr_data=qrdata.model_dump_json(),
            ticket_url=ticket_url,
        )
        await session.add(instance=new_ticket)

        attendee: User | None = await session.find_one_or_none(
            model=User, criteria=(Column("guid") == new_ticket.attendee_guid,)
        )
        if attendee and attendee.fcm_token:
            await fcm.send_push_notification(
                fcm_token=attendee.fcm_token,
                title=f"Get ready for {qrdata.event.name}",
                body=f"The host might ask for the QR code you can download here: {ticket_url} to show that's you!",
            )


async def upload_ticket_to_gcs(
    image_bytes: bytes,
    bucket_name: str,
    event_title: str | None,
) -> str:
    """Uploads ticket PNG to GCS and returns a public or signed URL."""
    storage_client: Client = Client()
    bucket: Bucket[Client] = storage_client.bucket(bucket_name)

    event_title = event_title if event_title else "PartyUp!"
    file_name: str = f"tickets/{event_title}/{uuid4()}.png"
    blob: Blob = bucket.blob(file_name)

    # Upload from memory
    blob.upload_from_string(image_bytes, content_type="image/png")

    # signed URLs (private but shareable)
    url: str = blob.generate_signed_url(
        version="v4", expiration=timedelta(hours=96), method="GET"
    )
    return url
