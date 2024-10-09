from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from . import models, schemas, cache
from typing import List, Optional
from datetime import datetime
import hashlib


def generate_cache_key(query: str, tags: Optional[List[str]], status: Optional[str], priority: Optional[str], 
                       from_date: Optional[datetime], to_date: Optional[datetime], user_id: int, page: int, size: int) -> str:
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
        str(size)
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
    size: int = 10
):
    cache_key = generate_cache_key(query, tags, status, priority, from_date, to_date, user_id, page, size)
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

    total = task_query.count()
    tasks = task_query.offset((page - 1) * size).limit(size).all()

    result = {
        'tasks': [task.to_dict() for task in tasks],  # Предполагается, что у модели Task есть метод to_dict()
        'total': total
    }
    cache.set_cache(cache_key, result, expiration=300)  # Кэшируем на 5 минут

    return tasks, total
