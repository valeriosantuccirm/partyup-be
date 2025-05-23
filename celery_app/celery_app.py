import os

from celery import Celery

celery_app = Celery(
    main="partyup",
    broker=f"redis://{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}/0",
    backend=f"redis://{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}/0",
)
# Update confs
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)
# Set priority 1 -10
celery_app.conf.broker_transport_options = {
    "priority_steps": list(range(1, 6)),
    "sep": ":",
    "queue_order_strategy": "sorted",
}
# Auto-discover tasks from all modules in the `celery_app/tasks` package
celery_app.autodiscover_tasks(packages=["celery_app.tasks"])
