from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas, notifications, auth
from .database import get_db
from .logger import logger

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
    await notifications.send_notification(current_user.username, f"New task created: {db_task.title}", 'task', db_task.id)
    logger.info(f"Task created successfully: {db_task.id}")
    return db_task

@router.get("/", response_model=List[schemas.Task])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"Fetching tasks with skip={skip} and limit={limit}")
    tasks = db.query(models.Task).offset(skip).limit(limit).all()
    return tasks

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

@router.get("/{task_id}/comments", response_model=List[schemas.Comment])
def read_task_comments(task_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"Fetching comments for task {task_id} with skip={skip} and limit={limit}")
    comments = db.query(models.Comment).filter(models.Comment.task_id == task_id).offset(skip).limit(limit).all()
    return comments

@router.get("/tags", response_model=List[schemas.Tag])
def read_tags(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"Fetching tags with skip={skip} and limit={limit}")
    tags = db.query(models.Tag).offset(skip).limit(limit).all()
    return tags