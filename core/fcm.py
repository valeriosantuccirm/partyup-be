from uuid import UUID

from firebase_admin import messaging
from firebase_admin._messaging_encoder import Message
from firebase_admin._messaging_utils import Notification


async def send_push_notification(
    fcm_token: str,
    title: str,
    body: str,
    follower_guid: UUID | None = None,
    image_url: str | None = None,
) -> str:
    """
    Send a Firebase push notification to a user with an image.

    Args:
        fcm_token (str): Firebase Cloud Messaging token of the recipient.
        title (str): Notification title.
        body (str): Notification message.
        image_url (str, optional): URL of the image to display in the notification.
    """
    notification: Notification = messaging.Notification(
        title=title,
        body=body,
        image=image_url,
    )
    message: Message = messaging.Message(
        notification=notification,
        token=fcm_token,
        data={
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "follower_guid": str(follower_guid),
        },
    )
    response: str = messaging.send(message=message)
    return response
