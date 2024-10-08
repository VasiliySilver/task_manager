from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("notifications", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.task_routes = {
    "app.tasks.*": "notifications-queue"
}