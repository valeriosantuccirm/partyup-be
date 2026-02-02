from datetime import datetime, timedelta
from uuid import uuid4

import stripe
from google.cloud.storage import (
    Bucket,
    Client,
)
from google.cloud.storage.blob import Blob
from sqlalchemy import Column

from cloud_funcs.payments.src.qrcode.generator import (
    create_partyup_ticket,
)
from cloud_funcs.payments.src.schema.qr_data import (
    BaseQRCodeData,
    BaseQRCodePaymentData,
    QRData,
)
from core import fcm
from core.config import settings
from core.database.crud.psql.psqlclient import PSQLClient
from core.database.models.psql.event import Event
from core.database.models.psql.payee_account import PayeeAccount
from core.database.models.psql.payment_intent import PaymentIntent
from core.database.models.psql.qr_ticket import QRTicket
from core.database.models.psql.scheduled_payment import ScheduledPayment
from core.database.models.psql.stripe_customer import StripeCustomer
from core.database.models.psql.user import User
from core.database.session import psqlclient
from core.datamodels.utils import from_stripe_amount_cents


async def make_payment(
    scheduled_payment: ScheduledPayment,
) -> QRData | None:
    session: PSQLClient = await anext(psqlclient())
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
    session: PSQLClient = await anext(psqlclient())
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
    bucket: Bucket[Client] = storage_client.bucket(bucket_name)  # type: ignore

    event_title = event_title if event_title else "PartyUp!"
    file_name: str = f"tickets/{event_title}/{uuid4()}.png"
    blob: Blob = bucket.blob(file_name)  # type: ignore
    # Upload from memory
    blob.upload_from_string(  # pyright: ignore[reportUnknownMemberType]
        image_bytes,
        content_type="image/png",
    )

    # signed URLs (private but shareable)
    url: str = blob.generate_signed_url(  # type: ignore
        version="v4",
        expiration=timedelta(hours=96),
        method="GET",
    )
    return url  # type: ignore
