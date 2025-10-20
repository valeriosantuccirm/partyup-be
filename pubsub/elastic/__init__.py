import json

from elasticsearch import Elasticsearch
from google.cloud import pubsub_v1

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path("your-gcp-project-id", "user-sync-sub")

# Setup Elasticsearch
es = Elasticsearch("http://localhost:9200")  # o URL GCP


def callback(message):
    user_data = json.loads(message.data.decode("utf-8"))
    print("Received user:", user_data)

    # Salva su Elasticsearch
    es.index(index="users", id=user_data["id"], document=user_data)
    print("User indexed in Elasticsearch")

    message.ack()


subscriber.subscribe(subscription_path, callback=callback)

print("Listening for new users...")

import time

while True:
    time.sleep(60)
