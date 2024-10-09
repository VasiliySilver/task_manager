from celery_app import celery_app
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
import logging

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка подключения к базе данных
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@db/taskdb')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Импорт моделей
from task_models import Task, Notification, Base

@celery_app.task
def check_due_tasks():
    db = SessionLocal()
    try:
        # Находим задачи, срок выполнения которых наступает в течение следующих 24 часов
        soon_due_tasks = db.query(Task).filter(
            and_(
                Task.due_date <= datetime.utcnow() + timedelta(hours=24),
                Task.due_date > datetime.utcnow(),
                Task.status != 'completed'
            )
        ).all()

        for task in soon_due_tasks:
            create_notification(db, task)

    finally:
        db.close()

def create_notification(db, task):
    notification = Notification(
        user_id=task.user_id,
        task_id=task.id,
        message=f"Task '{task.title}' is due in less than 24 hours!",
        created_at=datetime.utcnow()
    )
    db.add(notification)
    db.commit()
    logger.info(f"Created notification for task {task.id}")