from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas, tasks
from .database import get_db
from .auth import get_current_active_user
from .logger import logger
from datetime import datetime

router = APIRouter()

@router.post("/", response_model=schemas.Notification)
async def create_notification(notification: schemas.NotificationCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_active_user)):
    logger.info(f"Creating notification for user: {notification.user_id}")
    tasks.send_notification.delay(notification.user_id, notification.message, notification.type, notification.related_id)
    logger.info(f"Notification created and sent for user: {notification.user_id}")
    return {"id": 0, "user_id": notification.user_id, "message": notification.message, "type": notification.type, "related_id": notification.related_id, "created_at": datetime.utcnow(), "is_read": False}

@router.get("/user/{user_id}", response_model=List[schemas.Notification])
def read_user_notifications(user_id: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: dict = Depends(get_current_active_user)):
    logger.info(f"Fetching notifications for user: {user_id}")
    if current_user['username'] != user_id and current_user['role'] != 'admin':
        logger.warning(f"Unauthorized attempt to view notifications for user: {user_id} by user: {current_user['username']}")
        raise HTTPException(status_code=403, detail="Not authorized to view these notifications")
    notifications = db.query(models.Notification).filter(models.Notification.user_id == user_id).offset(skip).limit(limit).all()
    logger.info(f"Retrieved {len(notifications)} notifications for user: {user_id}")
    return notifications

@router.put("/{notification_id}/read", response_model=schemas.Notification)
def mark_notification_as_read(notification_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_active_user)):
    logger.info(f"Marking notification {notification_id} as read")
    notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if notification is None:
        logger.warning(f"Notification not found: {notification_id}")
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != current_user['username'] and current_user['role'] != 'admin':
        logger.warning(f"Unauthorized attempt to mark notification {notification_id} as read by user: {current_user['username']}")
        raise HTTPException(status_code=403, detail="Not authorized to update this notification")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    logger.info(f"Notification {notification_id} marked as read successfully")
    return notification