from celery import Celery
from celery.schedules import crontab
import os

celery_app = Celery('tasks',
                    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
                    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'))

celery_app.conf.beat_schedule = {
    'check-due-tasks': {
        'task': 'tasks.check_due_tasks',
        'schedule': 3600.0,  # Выполнять каждый час
    },
    'send-daily-summary': {
        'task': 'tasks.send_daily_summary',
        'schedule': crontab(hour=9, minute=0)  # Отправлять ежедневно в 9:00
    },
}

celery_app.conf.imports = ['tasks']
