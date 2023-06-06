from config import ENV
from data_manager import DataManager
from todoist import *

data_manager = DataManager(ENV['DATA_FILENAME'])


async def comment_added(comment: Comment):
    if not comment.content.startswith('existio:'):
        return
    tag = comment.content.splitlines()[0].split(':', maxsplit=1)[1].strip()
    if not tag:
        return
    data_manager.store(comment.item_id, tag)
    # TODO: delete comment
    # TODO: comment with a link to exist.io
    # TODO: comment with stats


async def task_completed(task: Task):
    tag = data_manager.get(task.id)
    if not tag:
        return
    # TODO: call exist.io
    # TODO: update stats


async def task_uncompleted(task: Task):
    tag = data_manager.get(task.id)
    if not tag:
        return
    # TODO: call exist.io
    # TODO: update stats
