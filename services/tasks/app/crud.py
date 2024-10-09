from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.orm import Session
from . import models, schemas, cache
from typing import List, Optional
from datetime import datetime
import hashlib


def generate_cache_key(query: str, tags: Optional[List[str]], status: Optional[str], priority: Optional[str], 
                       from_date: Optional[datetime], to_date: Optional[datetime], user_id: int, page: int, size: int,
                       sort: Optional[schemas.TaskSort]) -> str:
    """
    Generate a unique cache key based on search parameters.
    """
    key_parts = [
        query,
        ','.join(sorted(tags)) if tags else '',
        status or '',
        priority or '',
        str(from_date) if from_date else '',
        str(to_date) if to_date else '',
        str(user_id),
        str(page),
        str(size),
        f"{sort.field.value}_{sort.order.value}" if sort else ''
    ]
    return hashlib.md5('|'.join(key_parts).encode()).hexdigest()


def search_tasks(
    db: Session,
    query: str,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    user_id: int = None,
    page: int = 1,
    size: int = 10,
    sort: Optional[schemas.TaskSort] = None
):
    cache_key = generate_cache_key(query, tags, status, priority, from_date, to_date, user_id, page, size, sort)
    cached_result = cache.get_cache(cache_key)
    
    if cached_result:
        return cached_result['tasks'], cached_result['total']

    search_vector = func.to_tsvector('english', models.Task.title + ' ' + func.coalesce(models.Task.description, ''))
    search_query = func.plainto_tsquery('english', query)

    task_query = db.query(models.Task).filter(search_vector.match(search_query))

    if tags:
        task_query = task_query.join(models.Task.tags).filter(models.Tag.name.in_(tags))
    if status:
        task_query = task_query.filter(models.Task.status == status)
    if priority:
        task_query = task_query.filter(models.Task.priority == priority)
    if from_date:
        task_query = task_query.filter(models.Task.due_date >= from_date)
    if to_date:
        task_query = task_query.filter(models.Task.due_date <= to_date)
    if user_id:
        task_query = task_query.filter(models.Task.user_id == user_id)

    # Применяем сортировку
    if sort:
        sort_column = getattr(models.Task, sort.field.value)
        if sort.order == schemas.SortOrder.desc:
            task_query = task_query.order_by(desc(sort_column))
        else:
            task_query = task_query.order_by(asc(sort_column))
    else:
        # Сортировка по умолчанию
        task_query = task_query.order_by(desc(models.Task.created_at))

    total = task_query.count()
    tasks = task_query.offset((page - 1) * size).limit(size).all()

    result = {
        'tasks': [task.to_dict() for task in tasks],  # Предполагается, что у модели Task есть метод to_dict()
        'total': total
    }
    cache.set_cache(cache_key, result, expiration=300)  # Кэшируем на 5 минут

    return tasks, total

def get_user_notifications(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Notification)\
        .filter(models.Notification.user_id == user_id)\
        .order_by(models.Notification.created_at.desc())\
        .offset(skip).limit(limit).all()

def get_notification_summary(db: Session, user_id: int):
    total = db.query(func.count(models.Notification.id))\
        .filter(models.Notification.user_id == user_id).scalar()
    unread = db.query(func.count(models.Notification.id))\
        .filter(models.Notification.user_id == user_id)\
        .filter(models.Notification.is_read == False).scalar()
    return {"total": total, "unread": unread}

def get_dashboard_summary(db: Session, user_id: int):
    now = datetime.utcnow()
    today = now.date()
    week_ago = now - timedelta(days=7)

    notifications = get_notification_summary(db, user_id)
    tasks_due_today = db.query(func.count(models.Task.id))\
        .filter(models.Task.user_id == user_id)\
        .filter(func.date(models.Task.due_date) == today)\
        .filter(models.Task.status != 'completed').scalar()
    tasks_overdue = db.query(func.count(models.Task.id))\
        .filter(models.Task.user_id == user_id)\
        .filter(models.Task.due_date < now)\
        .filter(models.Task.status != 'completed').scalar()
    tasks_completed_this_week = db.query(func.count(models.Task.id))\
        .filter(models.Task.user_id == user_id)\
        .filter(models.Task.status == 'completed')\
        .filter(models.Task.updated_at >= week_ago).scalar()

    return schemas.DashboardSummary(
        notifications=schemas.NotificationSummary(**notifications),
        tasks_due_today=tasks_due_today,
        tasks_overdue=tasks_overdue,
        tasks_completed_this_week=tasks_completed_this_week
    )

def mark_notification_as_read(db: Session, notification_id: int, user_id: int):
    notification = db.query(models.Notification)\
        .filter(models.Notification.id == notification_id)\
        .filter(models.Notification.user_id == user_id)\
        .first()
    if notification:
        notification.is_read = True
        db.commit()
    return notification
