from typing import Any, List

from pydantic import BaseModel

__all__ = [
    'API_VERSION',
    'Comment',
    'Initiator',
    'Task',
    'Webhook',
]

API_VERSION = '9'


class Due(BaseModel):
    date: str
    is_recurring: bool
    lang: str
    string: str
    timezone: Any


class Task(BaseModel):
    added_by_uid: str
    assigned_by_uid: Any
    checked: bool
    child_order: int
    collapsed: bool
    content: str
    description: str
    added_at: str
    completed_at: Any
    due: Due | None
    id: str
    is_deleted: bool
    labels: List
    parent_id: Any
    priority: int
    project_id: str
    responsible_uid: Any
    section_id: Any
    sync_id: Any
    url: str | None
    user_id: str


class Comment(BaseModel):
    content: str
    item_id: str


class Initiator(BaseModel):
    email: str
    full_name: str
    id: str
    image_id: str
    is_premium: bool


class Webhook(BaseModel):
    event_name: str
    user_id: str
    event_data: Task | Comment
    initiator: Initiator
    version: str

    class Config:
        schema_extra = {
            "example": {
                "event_name": "item:completed",
                "user_id": "2671355",
                "event_data": {
                    "added_by_uid": "2671355",
                    "assigned_by_uid": None,
                    "checked": False,
                    "child_order": 3,
                    "collapsed": False,
                    "content": "Buy Milk",
                    "description": "",
                    "added_at": "2021-02-10T10:33:38.000000Z",
                    "completed_at": None,
                    "due": None,
                    "id": "2995104339",
                    "is_deleted": False,
                    "labels": [],
                    "parent_id": None,
                    "priority": 1,
                    "project_id": "2203306141",
                    "responsible_uid": None,
                    "section_id": None,
                    "sync_id": None,
                    "url": "https://todoist.com/showTask?id=2995104339",
                    "user_id": "2671355",
                },
                "initiator": {
                    "email": "alice@example.com",
                    "full_name": "Alice",
                    "id": "2671355",
                    "image_id": "ad38375bdb094286af59f1eab36d8f20",
                    "is_premium": True,
                },
                "version": "9",
            },
        }
