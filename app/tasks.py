from datetime import datetime, timedelta, date

from todoist_api_python.api_async import TodoistAPIAsync

from data_manager import DataManager
from existio import ExistioAPI, AttributeValue
from todoist import *

EMOJI_FUTURE = '⬜'
EMOJI_TODAY = '❓'
EMOJI_SUCCEED = '✅'
EMOJI_FAILED = '❌'

EMOJIS = [
    EMOJI_FUTURE,
    EMOJI_TODAY,
    EMOJI_SUCCEED,
    EMOJI_FAILED,
]

DAY_SLICE_HOUR = 5  # next day starts at this hour


def current_date():
    now = datetime.utcnow()
    if now.hour < DAY_SLICE_HOUR:
        now = now - timedelta(hours=DAY_SLICE_HOUR + 1)
    return now.strftime('%Y-%m-%d')


async def generate_stats(tag, existio_api: ExistioAPI):
    today = date.today()
    date_min = today - timedelta(weeks=2, days=today.weekday())  # get information for the last 3 weeks
    values = await existio_api.attribute_values(tag, date_min=date_min, date_max=today)
    result = ""
    curr_date = date_min
    end_of_week = today + timedelta(days=6 - today.weekday())
    while curr_date <= end_of_week:
        if curr_date > today:
            result += EMOJI_FUTURE
        elif values.get(curr_date):
            result += EMOJI_SUCCEED
        elif curr_date == today:
            result += EMOJI_TODAY
        else:
            result += EMOJI_FAILED
        if curr_date.weekday() == 6:
            # Sunday - new line
            result += '\n'
        curr_date += timedelta(days=1)
    return result


async def find_stats_comment(task_id, todoist_api: TodoistAPIAsync) -> int or None:
    comments = await todoist_api.get_comments(task_id=task_id)
    if not comments:
        return
    comment = comments[-1]
    for emoji in EMOJIS:
        if comment.content.find(emoji) != -1:
            return comment.id


async def comment_added(
        comment: Comment,
        data_manager: DataManager,
        todoist_api: TodoistAPIAsync,
        existio_api: ExistioAPI,
):
    if not comment.content.startswith('existio:'):
        return
    text = comment.content.strip()
    if not text:
        return
    tag = text.splitlines()[0].split(':', maxsplit=1)[1].strip()
    task_id = comment.item_id
    if tag == '-':
        # release tag
        await data_manager.remove(task_id)
        return
    tag = tag.strip('-').replace(' ', '_')
    if not tag:
        return
    await data_manager.store(task_id, tag)
    await todoist_api.delete_comment(comment.id)
    await todoist_api.add_comment(existio_api.get_tag_url(tag), task_id=task_id)
    await existio_api.attributes_acquire([tag])
    stats = await generate_stats(tag, existio_api)
    await todoist_api.add_comment(stats, task_id=task_id)


async def task_completed(
        task: Task,
        data_manager: DataManager,
        todoist_api: TodoistAPIAsync,
        existio_api: ExistioAPI,
):
    tag = await data_manager.get(task.id)
    if not tag:
        return
    await existio_api.attributes_update([
        AttributeValue(name=tag, date=current_date()),
    ])
    stats = await generate_stats(tag, existio_api)
    task_id = task.id
    comment_id = await find_stats_comment(task_id, todoist_api)
    if comment_id:
        await todoist_api.update_comment(comment_id, stats, task_id=task_id)
    else:
        await todoist_api.add_comment(stats, task_id=task_id)


async def task_uncompleted(
        task: Task,
        data_manager: DataManager,
        todoist_api: TodoistAPIAsync,
        existio_api: ExistioAPI,
):
    tag = await data_manager.get(task.id)
    if not tag:
        return
    await existio_api.attributes_update([
        AttributeValue(name=tag, date=current_date(), value=0),
    ])
    stats = await generate_stats(tag, existio_api)
    task_id = task.id
    comment_id = await find_stats_comment(task_id, todoist_api)
    if comment_id:
        await todoist_api.update_comment(comment_id, stats, task_id=task_id)
    else:
        await todoist_api.add_comment(stats, task_id=task_id)


async def task_deleted(
        task: Task,
        data_manager: DataManager,
        todoist_api: TodoistAPIAsync,
        existio_api: ExistioAPI,
):
    tag = await data_manager.get(task.id)
    if not tag:
        return
    await data_manager.remove(task.id)
    await existio_api.attributes_release([tag])


EVEN_MAP = {
    'note:added': comment_added,
    'item:completed': task_completed,
    'item:uncompleted': task_uncompleted,
    'item:deleted': task_deleted,
}
