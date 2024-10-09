from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas, notifications, auth
from .database import get_db
from .logger import logger

router = APIRouter()

@router.post("/", response_model=schemas.Project)
async def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_active_user)):
    logger.info(f"Creating new project for user: {current_user.username}")
    db_project = models.Project(**project.dict(), owner_id=current_user.username)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    await notifications.send_project_notification(db_project.id, f"New project created: {db_project.name}")
    logger.info(f"Project created successfully: {db_project.id}")
    return db_project

@router.get("/", response_model=List[schemas.Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"Fetching projects with skip={skip} and limit={limit}")
    projects = db.query(models.Project).offset(skip).limit(limit).all()
    return projects

@router.get("/{project_id}", response_model=schemas.ProjectWithTasks)
def read_project(project_id: int, db: Session = Depends(get_db)):
    logger.info(f"Fetching project with id: {project_id}")
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if project is None:
        logger.warning(f"Project not found: {project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=schemas.Project)
def update_project(project_id: int, project: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    logger.info(f"Updating project: {project_id}")
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project is None:
        logger.warning(f"Project not found: {project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in project.dict().items():
        setattr(db_project, key, value)
    db.commit()
    db.refresh(db_project)
    logger.info(f"Project {project_id} updated successfully")
    return db_project

@router.delete("/{project_id}", response_model=schemas.Project)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    logger.info(f"Deleting project: {project_id}")
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project is None:
        logger.warning(f"Project not found: {project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(db_project)
    db.commit()
    logger.info(f"Project {project_id} deleted successfully")
    return db_project

@router.post("/{project_id}/members/{user_id}", response_model=schemas.Project)
async def add_project_member(project_id: int, user_id: str, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_active_user)):
    logger.info(f"Adding member {user_id} to project {project_id}")
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if project is None:
        logger.warning(f"Project not found: {project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.username and current_user.role != 'admin':
        logger.warning(f"Unauthorized attempt to add member to project {project_id} by user {current_user.username}")
        raise HTTPException(status_code=403, detail="Not authorized to add members to this project")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    project.members.append(user)
    db.commit()
    db.refresh(project)
    await notifications.send_project_notification(project.id, f"New member added to project: {project.name}")
    logger.info(f"Member {user_id} added successfully to project {project_id}")
    return project