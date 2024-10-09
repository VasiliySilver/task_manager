from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from datetime import datetime
from . import models, schemas, notifications, auth, crud
from .database import get_db
from .logger import logger
from .elasticsearch import search_tasks as es_search_tasks, index_task
from math import ceil

router = APIRouter()

@router.post("/", response_model=schemas.Task)
async def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_active_user)):
    logger.info(f"Creating new task for user: {current_user.username}")
    db_task = models.Task(**task.dict(exclude={"tags"}), user_id=current_user.username)
    for tag_name in task.tags:
        tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
        if not tag:
            tag = models.Tag(name=tag_name)
            db.add(tag)
        db_task.tags.append(tag)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    index_task(db_task)  # Индексируем задачу в Elasticsearch
    await notifications.send_notification(current_user.username, f"New task created: {db_task.title}", 'task', db_task.id)
    logger.info(f"Task created successfully: {db_task.id}")
    return db_task

@router.get("/", response_model=schemas.PaginatedResponse[schemas.Task])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"Fetching tasks with skip={skip} and limit={limit}")
    total = db.query(func.count(models.Task.id)).scalar()
    tasks = db.query(models.Task).offset(skip).limit(limit).all()
    return schemas.PaginatedResponse(
        items=tasks,
        total=total,
        page=skip // limit + 1,
        size=limit
    )

@router.get("/{task_id}", response_model=schemas.Task)
def read_task(task_id: int, db: Session = Depends(get_db)):
    logger.info(f"Fetching task with id: {task_id}")
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task is None:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/{task_id}", response_model=schemas.Task)
async def update_task(task_id: int, task: schemas.TaskUpdate, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_active_user)):
    logger.info(f"Updating task {task_id} for user: {current_user.username}")
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.user_id != current_user.username and current_user.role != 'admin':
        logger.warning(f"Unauthorized update attempt on task {task_id} by user {current_user.username}")
        raise HTTPException(status_code=403, detail="Not authorized to update this task")
    for key, value in task.dict(exclude={"tags"}).items():
        setattr(db_task, key, value)
    
    db_task.tags.clear()
    for tag_name in task.tags:
        tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
        if not tag:
            tag = models.Tag(name=tag_name)
            db.add(tag)
        db_task.tags.append(tag)
    
    db.commit()
    db.refresh(db_task)
    index_task(db_task)  # Обновляем индекс в Elasticsearch
    await notifications.send_notification(db_task.user_id, f"Task updated: {db_task.title}", 'task', db_task.id)
    logger.info(f"Task {task_id} updated successfully")
    return db_task

@router.delete("/{task_id}", response_model=schemas.Task)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    logger.info(f"Deleting task: {task_id}")
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    # Удаление из Elasticsearch не требуется, так как документ будет автоматически удален при следующей индексации
    logger.info(f"Task {task_id} deleted successfully")
    return db_task

@router.post("/{task_id}/comments", response_model=schemas.Comment)
async def create_comment(task_id: int, comment: schemas.CommentCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating new comment for task: {task_id}")
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    db_comment = models.Comment(**comment.dict(), task_id=task_id, user_id=1)  # Hardcoded user_id for now
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    await notifications.send_notification(db_task.user_id, f"New comment on task: {db_task.title}", 'comment', db_comment.id)
    logger.info(f"Comment created successfully for task {task_id}")
    return db_comment

@router.get("/{task_id}/comments", response_model=schemas.PaginatedResponse[schemas.Comment])
def read_task_comments(task_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"Fetching comments for task {task_id} with skip={skip} and limit={limit}")
    total = db.query(func.count(models.Comment.id)).filter(models.Comment.task_id == task_id).scalar()
    comments = db.query(models.Comment).filter(models.Comment.task_id == task_id).offset(skip).limit(limit).all()
    return schemas.PaginatedResponse(
        items=comments,
        total=total,
        page=skip // limit + 1,
        size=limit
    )

@router.get("/tags", response_model=schemas.PaginatedResponse[schemas.Tag])
def read_tags(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"Fetching tags with skip={skip} and limit={limit}")
    total = db.query(func.count(models.Tag.id)).scalar()
    tags = db.query(models.Tag).offset(skip).limit(limit).all()
    return schemas.PaginatedResponse(
        items=tags,
        total=total,
        page=skip // limit + 1,
        size=limit
    )

@router.get("/tags/all", response_model=List[schemas.Tag])
async def get_all_tags(
    db: Session = Depends(get_db),
    current_user: auth.TokenData = Depends(auth.get_current_active_user)
):
    logger.info("Fetching all tags")
    tags = db.query(models.Tag).all()
    return tags

@router.get("/search", response_model=schemas.PaginatedResponse)
async def search_tasks(
    query: str = Query(..., min_length=1),
    tags: List[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: auth.TokenData = Depends(auth.get_current_active_user)
):
    logger.info(f"Searching tasks with query: {query}, tags: {tags}, status: {status}, priority: {priority}, from_date: {from_date}, to_date: {to_date}, page: {page}, size: {size}")
    
    tasks, total = crud.search_tasks(
        db, query, tags, status, priority, from_date, to_date, 
        user_id=current_user.id, page=page, size=size
    )
    
    return {
        "items": tasks,
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size)
    }

@router.post("/filter", response_model=schemas.PaginatedResponse[schemas.Task])
async def filter_tasks(
    filter_params: schemas.TaskFilter,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: auth.TokenData = Depends(auth.get_current_active_user)
):
    logger.info(f"Filtering tasks with params: {filter_params}")
    
    query = db.query(models.Task)

    if filter_params.title:
        query = query.filter(models.Task.title.ilike(f"%{filter_params.title}%"))
    if filter_params.status:
        query = query.filter(models.Task.status == filter_params.status)
    if filter_params.priority:
        query = query.filter(models.Task.priority == filter_params.priority)
    if filter_params.tags:
        query = query.join(models.Task.tags).filter(models.Tag.name.in_(filter_params.tags))

    total = query.count()
    tasks = query.offset(skip).limit(limit).all()
    return schemas.PaginatedResponse(
        items=tasks,
        total=total,
        page=skip // limit + 1,
        size=limit
    )

@router.get("/stats", response_model=schemas.TaskStats)
async def get_task_stats(
    db: Session = Depends(get_db),
    current_user: auth.TokenData = Depends(auth.get_current_active_user)
):
    total_tasks = db.query(func.count(models.Task.id)).filter(models.Task.user_id == current_user.id).scalar()
    tasks_by_status = db.query(
        models.Task.status, func.count(models.Task.id)
    ).filter(models.Task.user_id == current_user.id).group_by(models.Task.status).all()
    tasks_by_priority = db.query(
        models.Task.priority, func.count(models.Task.id)
    ).filter(models.Task.user_id == current_user.id).group_by(models.Task.priority).all()
    overdue_tasks = db.query(func.count(models.Task.id)).filter(
        and_(models.Task.user_id == current_user.id, models.Task.due_date < func.now(), models.Task.status != 'completed')
    ).scalar()

    return {
        "total_tasks": total_tasks,
        "tasks_by_status": dict(tasks_by_status),
        "tasks_by_priority": dict(tasks_by_priority),
        "overdue_tasks": overdue_tasks
    }