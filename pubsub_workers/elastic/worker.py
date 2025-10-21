import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from google.cloud import pubsub_v1
from google.oauth2 import service_account

from app.config import settings
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.models.elasticsearch.es_user import ESUser
from app.datamodels.schemas.pubsub import PubSubUserMsg

PROJECT_ID = "partyup-be-aaf0d"
SUBSCRIPTION_ID = "elastic-users-sub"


# Define a synchronous callback and delegate to asyncio
def sync_callback_wrapper(esloop):
    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        print(f"Received message: {message.data.decode('utf-8')}")
        asyncio.run_coroutine_threadsafe(process_message(message), esloop)

    return callback


# Async logic for processing a message
async def process_message(message: pubsub_v1.subscriber.message.Message) -> None:
    esclient: ElasticsearchClient = ElasticsearchClient()
    try:
        data = PubSubUserMsg(**json.loads(message.data.decode("utf-8")))
        if data.event == "update":
            user: ESUser | None = await esclient.find(
                index=settings.ES_USERS_INDEX,
                query=common_q.find_by_attr(guid=data.instance.guid),
                model=ESUser,
                one=True,
            )
            if not user:
                raise
            updated_data: dict[str, Any] = {
                **user.model_dump(),
                **data.instance.model_dump(),
            }
            await esclient.update(
                index=settings.ES_USERS_INDEX,
                doc_id=user.id,
                **updated_data,
            )
        print(f"Processing data: {data}")

        message.ack()
        await esclient.add(
            index=settings.ES_USERS_INDEX,
            instance=data.instance,
        )
        message.ack()
    except Exception as e:
        print(f"Error processing message: {e}")
        message.nack()

async def run_worker():
    credentials = service_account.Credentials.from_service_account_file(
        "/Users/valerio.santucci/personal/repo/partyup-be/.creds/partyup-be-privatekey-pubsub.json"
    )
    subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

    # Pass current asyncio loop into sync callback
    loop = asyncio.get_running_loop()
    callback = sync_callback_wrapper(loop)

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"Listening for messages on {subscription_path}...\n")

    # Run the blocking `result()` in a background thread so we can await it
    with ThreadPoolExecutor() as executor:
        try:
            await loop.run_in_executor(executor, streaming_pull_future.result)
        except asyncio.CancelledError:
            print("Worker cancelled. Shutting down...")
            streaming_pull_future.cancel()

# Async main entry point
async def main():
    try:
        await run_worker()
    except KeyboardInterrupt:
        print("Worker stopped by user.")

if __name__ == "__main__":
    asyncio.run(main())
