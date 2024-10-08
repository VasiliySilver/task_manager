from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas, tasks
from .database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.Notification)
def create_notification(notification: schemas.NotificationCreate, db: Session = Depends(get_db)):
    tasks.send_notification.delay(notification.user_id, notification.message)
    return {"id": 0, "user_id": notification.user_id, "message": notification.message, "created_at": datetime.utcnow(), "is_read": False}

@router.get("/user/{user_id}", response_model=List[schemas.Notification])
def read_user_notifications(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    notifications = db.query(models.Notification).filter(models.Notification.user_id == user_id).offset(skip).limit(limit).all()
    return notifications

@router.put("/{notification_id}/read", response_model=schemas.Notification)
def mark_notification_as_read(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification