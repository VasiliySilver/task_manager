from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional
from datetime import datetime


def search_tasks(
    db: Session,
    query: str,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    user_id: Optional[int] = None,
    page: int = 1,
    size: int = 10
):
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

    total = task_query.count()
    tasks = task_query.offset((page - 1) * size).limit(size).all()

    return tasks, total
