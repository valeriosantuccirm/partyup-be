from celery import Celery

celery_app = Celery(
    main="partyup",
    broker="redis://localhost:6379/0",  # Adjust as needed
    backend="redis://localhost:6379/0",  # Optional: for result backend
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Auto-discover tasks from all modules in the `celery_app/tasks` package
celery_app.autodiscover_tasks(packages=["celery_app.tasks"])
