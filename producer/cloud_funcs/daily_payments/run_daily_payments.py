from producer.cloud_funcs.daily_payments.publish import publish_message
from producer.enums.topics import GCPTopics


async def run_daily_payments() -> None:
    message: dict[str, str] = {
        "event": GCPTopics.DP.value,
    }
    await publish_message(
        topic_name=GCPTopics.DP,
        message=message,
    )
