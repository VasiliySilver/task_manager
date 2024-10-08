from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class UserBase(BaseModel):
    username: str

class User(UserBase):
    id: int

    class Config:
        orm_mode = True

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    owner_id: int
    owner: User
    members: List[User] = []

    class Config:
        orm_mode = True

class ProjectWithTasks(Project):
    tasks: List['Task'] = []

class TaskBase(BaseModel):
    title: str

class Task(TaskBase):
    id: int
    project_id: int

    class Config:
        orm_mode = True

ProjectWithTasks.update_forward_refs()