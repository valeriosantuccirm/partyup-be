import asyncio

from google.cloud import pubsub_v1

from consumers.workers.main import handle_pubsub_message

PROJECT_ID = "partyup-be-aaf0d"
SUBSCRIPTION_ID = "elastic-users-sub"


async def callback(message):
    """Funzione asincrona per processare i messaggi Pub/Sub"""
    print(f"📨 Received message: {message.data}")
    try:
        await handle_pubsub_message(message, {})
        message.ack()
        print("✅ Message processed and acknowledged")
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        message.nack()


async def async_main():
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
    print(f"👂 Listening on {subscription_path} ...")

    loop = asyncio.get_running_loop()  # loop principale

    # callback wrapper che invia la coroutine nel loop principale
    def thread_callback(msg):
        asyncio.run_coroutine_threadsafe(callback(msg), loop)

    streaming_pull_future = subscriber.subscribe(subscription_path, thread_callback)

    try:
        # blocca finché non viene interrotto (Ctrl+C)
        await asyncio.get_running_loop().run_in_executor(
            None, streaming_pull_future.result
        )
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
        print("👋 Worker stopped")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
