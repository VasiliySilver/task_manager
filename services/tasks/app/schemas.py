from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum

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

class TaskStats(BaseModel):
    total_tasks: int
    tasks_by_status: Dict[str, int]
    tasks_by_priority: Dict[str, int]
    overdue_tasks: int

class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"

class TaskSortField(str, Enum):
    title = "title"
    status = "status"
    priority = "priority"
    due_date = "due_date"
    created_at = "created_at"
    updated_at = "updated_at"

class TaskSort(BaseModel):
    field: TaskSortField
    order: SortOrder = SortOrder.asc

class UserUpdate(BaseModel):
    email: Optional[str] = None
    fcm_token: Optional[str] = None