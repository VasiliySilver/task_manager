from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Index, text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

task_tags = Table('task_tags', Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id')),
    Column('tag_id', Integer, ForeignKey('tags.id')),
    Index('idx_task_tags', 'task_id', 'tag_id')
)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    due_date = Column(DateTime)
    start_date = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="tasks")
    tags = relationship("Tag", secondary="task_tags", back_populates="tasks")

    __table_args__ = (
        Index('idx_task_search', 
              text('to_tsvector(\'english\', title || \' \' || coalesce(description, \'\'))'),
              postgresql_using='gin'),
        Index('idx_task_status_priority', 'status', 'priority'),
        Index('idx_task_due_date', 'due_date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'tags': [tag.name for tag in self.tags]
        }

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    fcm_token = Column(String)
    username = Column(String, unique=True, index=True)

    tasks = relationship("Task", back_populates="user")

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    tasks = relationship("Task", secondary=task_tags, back_populates="tags")

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    task = relationship("Task", back_populates="comments")
    user = relationship("User")