from celery_app import celery_app
from task_models import User
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
import logging
from notifications import send_email, send_push_notification

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
    user = db.query(User).filter(User.id == task.user_id).first()
    if not user:
        logger.error(f"User not found for task {task.id}")
        return

    notification_settings = user.notification_settings
    hours_until_due = (task.due_date - datetime.utcnow()).total_seconds() / 3600

    if hours_until_due <= notification_settings['due_soon']:
        message = f"Task '{task.title}' is due in less than {notification_settings['due_soon']} hours!"
        notification = Notification(
            user_id=user.id,
            task_id=task.id,
            message=message,
            created_at=datetime.utcnow()
        )
        db.add(notification)
        db.commit()
        logger.info(f"Created notification for task {task.id}")

        if notification_settings['email']:
            send_email(user.email, "Task Due Soon", message)

        if notification_settings['push'] and user.fcm_token:
            send_push_notification(user.fcm_token, "Task Due Soon", message)

@celery_app.task
def send_daily_summary():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.notification_settings['daily_summary'].astext == 'true').all()
        for user in users:
            tasks = db.query(Task).filter(
                Task.user_id == user.id,
                Task.due_date <= datetime.utcnow() + timedelta(days=1),
                Task.status != 'completed'
            ).all()
            
            if tasks:
                message = "Your tasks due in the next 24 hours:\n"
                for task in tasks:
                    message += f"- {task.title}\n"
                
                if user.notification_settings['email']:
                    send_email(user.email, "Daily Task Summary", message)
                
                if user.notification_settings['push'] and user.fcm_token:
                    send_push_notification(user.fcm_token, "Daily Task Summary", message)
    finally:
        db.close()

@celery_app.task
def activate_pending_tasks():
    db = SessionLocal()
    try:
        pending_tasks = get_pending_tasks(db)
        for task in pending_tasks:
            updated_task = check_and_update_delayed_task_status(db, task.id)
            if updated_task.status == TaskStatus.active:
                # Отправляем уведомление пользователю
                user = db.query(User).filter(User.id == updated_task.user_id).first()
                if user:
                    message = f"Your delayed task '{updated_task.title}' has been activated."
                    notification = Notification(
                        user_id=user.id,
                        task_id=updated_task.id,
                        message=message,
                        created_at=datetime.utcnow()
                    )
                    db.add(notification)
                    
                    if user.notification_settings['email']:
                        send_email(user.email, "Delayed Task Activated", message)
                    
                    if user.notification_settings['push'] and user.fcm_token:
                        send_push_notification(user.fcm_token, "Delayed Task Activated", message)
        
        db.commit()
    finally:
        db.close()

# Добавим новую задачу в расписание Celery
celery_app.conf.beat_schedule['send-daily-summary'] = {
    'task': 'tasks.send_daily_summary',
    'schedule': crontab(hour=9, minute=0)  # Отправлять ежедневно в 9:00
}

celery_app.conf.beat_schedule['activate-pending-tasks'] = {
    'task': 'tasks.activate_pending_tasks',
    'schedule': 300.0  # Выполнять каждые 5 минут
}