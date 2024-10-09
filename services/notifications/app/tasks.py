from .celery_app import celery_app
from .database import SessionLocal
from . import models

@celery_app.task
def send_notification(user_id: str, message: str, notification_type: str, related_id: int):
    db = SessionLocal()
    try:
        notification = models.Notification(
            user_id=user_id,
            message=message,
            type=notification_type,
            related_id=related_id
        )
        db.add(notification)
        db.commit()
        # Here you would typically integrate with an external service to send the actual notification
        # (e.g., email service, push notification service)
        print(f"Sending notification to user {user_id}: {message}")
    finally:
        db.close()

@celery_app.task
def send_project_notifications(project_id: int, message: str):
    db = SessionLocal()
    try:
        # Здесь мы должны получить всех участников проекта
        # Предположим, что у нас есть таблица project_members с полями project_id и user_id
        project_members = db.query(models.ProjectMember).filter(models.ProjectMember.project_id == project_id).all()
        for member in project_members:
            send_notification.delay(member.user_id, message, 'project', project_id)
    finally:
        db.close()
