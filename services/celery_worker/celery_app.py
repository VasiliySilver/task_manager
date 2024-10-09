from celery import Celery
import os

celery_app = Celery('tasks',
                    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
                    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'))

celery_app.conf.beat_schedule = {
    'check-due-tasks': {
        'task': 'tasks.check_due_tasks',
        'schedule': 3600.0,  # Выполнять каждый час
    },
}

celery_app.conf.imports = ['tasks']
