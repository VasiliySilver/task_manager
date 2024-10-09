from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class TagBase(BaseModel):
    name: str

class TagCreate(TagBase):
    pass

class Tag(TagBase):
    id: int

    class Config:
        orm_mode = True

class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    pass

class Comment(CommentBase):
    id: int
    created_at: datetime
    task_id: int
    user_id: int

    class Config:
        orm_mode = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase):
    tags: List[str] = []

class TaskUpdate(TaskBase):
    tags: List[str] = []

class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    user_id: int
    tags: List[Tag] = []
    comments: List[Comment] = []

    class Config:
        orm_mode = True

class TaskFilter(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None

class TaskSearch(BaseModel):
    query: str
    tags: Optional[List[str]] = None

class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    size: int
    pages: int