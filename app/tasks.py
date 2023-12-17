from datetime import datetime, timedelta, date

from todoist_api_python.api_async import TodoistAPIAsync

import utils
from data_manager import DataManager
from existio import ExistioAPI, AttributeValue
from todoist import Comment, Task

EMOJI_STATS = '📊'
EMOJI_EMPTY = '⬜'
EMOJI_TODAY = '❓'
EMOJI_SUCCEED = '✅'
EMOJI_FAILED = '❌'

EMOJIS = [
    EMOJI_STATS,
    EMOJI_EMPTY,
    EMOJI_TODAY,
    EMOJI_SUCCEED,
    EMOJI_FAILED,
]

DAY_SLICE_HOUR = 5  # next day starts at this hour
DAY_TILL_UPDATE_PREVIOUS_MONTH = 10  # till this day of the month we update previous month stats
SHOW_DAYS_IN_DESCRIPTION = 16  # show this amount of days in description
PREVIOUS_MONTHS_STATS = 2
STATS_HEADER_FORMAT = '# {month} {year} {emoji}'
STATS_SUMMARY_FORMAT = '`{EMOJI_SUCCEED} {succeed} {EMOJI_FAILED} {failed}%s`'
STATS_SUMMARY_WITH_UNKNOWN_FORMAT = STATS_SUMMARY_FORMAT % ' {EMOJI_EMPTY} {unknown}'
STATS_SUMMARY_FORMAT %= ''
PREFIX_COMMAND = 'existio:'  # This is being interpreted as a command
EXIST_PART_URL = '/exist.io/'


def local_now():
    now = datetime.now()
    if now.hour < DAY_SLICE_HOUR:
        now = now - timedelta(hours=DAY_SLICE_HOUR + 1)
    return now


def current_date():
    return utils.format_date(local_now())


def generate_stats_header(month: date):
    return STATS_HEADER_FORMAT.format(
        month=month.strftime('%B'),
        year=month.year,
        emoji=EMOJI_STATS,
    )


def generate_stats_summary(succeed: int, failed: int, unknown: int = None):
    template = STATS_SUMMARY_FORMAT if unknown is None else STATS_SUMMARY_WITH_UNKNOWN_FORMAT
    return template.format(
        EMOJI_SUCCEED=EMOJI_SUCCEED,
        EMOJI_FAILED=EMOJI_FAILED,
        EMOJI_EMPTY=EMOJI_EMPTY,
        succeed=succeed,
        failed=failed,
        unknown=unknown,
    )


async def generate_stats(tag, month: date, existio_api: ExistioAPI) -> (int, str):
    assert month.day == 1
    month_end = month + timedelta(days=31)
    month_end -= timedelta(days=month_end.day)
    today = date.today()

    values = await existio_api.attribute_values(tag, date_min=month, date_max=month_end)
    succeed = failed = unknown = 0
    # empty days in the beginning of the month for the offset
    calendar = month.weekday() * EMOJI_EMPTY
    curr_date = month
    while curr_date <= month_end:
        if curr_date > today:
            unknown += 1
            calendar += EMOJI_EMPTY
        elif values.get(curr_date):
            succeed += 1
            calendar += EMOJI_SUCCEED
        elif curr_date == today:
            unknown += 1
            calendar += EMOJI_TODAY
        else:
            failed += 1
            calendar += EMOJI_FAILED
        if curr_date.weekday() == 6:
            # Sunday - new line
            calendar += '\n'
        curr_date += timedelta(days=1)
    if month != today.replace(day=1):
        unknown = None
    header = generate_stats_header(month)
    summary = generate_stats_summary(succeed, failed, unknown=unknown)
    return succeed, f'{header}\n{summary}\n{calendar}'


async def generate_description(tag, existio_api: ExistioAPI, show_days: int = None) -> str:
    today = date_min = date.today()
    date_min -= timedelta(days=show_days or SHOW_DAYS_IN_DESCRIPTION)

    values = await existio_api.attribute_values(tag, date_min=date_min, date_max=today)
    description = ''
    curr_date = today
    while curr_date >= date_min:
        if values.get(curr_date):
            description += EMOJI_SUCCEED
        elif curr_date == today:
            description += EMOJI_TODAY
        else:
            description += EMOJI_FAILED
        curr_date -= timedelta(days=1)
    return description


async def post_stats(task_id: str, tag: str, todoist_api: TodoistAPIAsync, existio_api: ExistioAPI,
                     update_months: int = None):
    if update_months is None:
        update_months = PREVIOUS_MONTHS_STATS
    today = date.today()
    current_month = today - timedelta(days=today.day - 1)
    previous_month = current_month - timedelta(days=1)
    previous_month -= timedelta(days=previous_month.day - 1)
    months = [
        current_month - timedelta(days=30 * i)
        for i in range(update_months + 1)
    ]
    months = [
        # set first day of the month
        month - timedelta(days=month.day - 1)
        for month in months
    ]
    months = list(reversed(months))
    # print(f'{months = }')
    generate_months = []
    delete_comment_ids = []
    comments = await todoist_api.get_comments(task_id=task_id)
    for month in months:
        need_update = month == current_month \
                      or month == previous_month and today.day < DAY_TILL_UPDATE_PREVIOUS_MONTH
        header = generate_stats_header(month)
        if need_update:
            for comment in comments:
                if utils.string_contains(comment.content, header):
                    delete_comment_ids.append(comment.id)
            generate_months.append(month)
        else:
            for comment in comments:
                if utils.string_contains(comment.content, header):
                    break
            else:
                # if such month does not exist
                generate_months.append(month)
    # print(f'{delete_comment_ids = }')
    # print(f'{generate_months = }')
    for comment_id in delete_comment_ids:
        await todoist_api.delete_comment(comment_id)
    texts = []
    have_succeed_before = False
    for month in generate_months:
        succeed, text = await generate_stats(tag, month, existio_api)
        if succeed:
            have_succeed_before = True
        elif not have_succeed_before:
            continue
        await todoist_api.add_comment(text, task_id=task_id)
        texts.append(text)
    description = await generate_description(tag, existio_api)
    texts.append(description)
    await todoist_api.update_task(task_id, description=description)
    return texts


async def comment_added(
        comment: Comment,
        data_manager: DataManager,
        todoist_api: TodoistAPIAsync,
        existio_api: ExistioAPI,
):
    text = comment.content.strip().lower()
    if not text.startswith(PREFIX_COMMAND):
        return
    comment_id = comment.id
    task_id = comment.item_id
    command = text[len(PREFIX_COMMAND):].strip()
    await process_command(command, task_id, comment_id, data_manager, todoist_api, existio_api)


async def process_command(
        command: str,
        task_id: str,
        comment_id: str | None,
        data_manager: DataManager,
        todoist_api: TodoistAPIAsync,
        existio_api: ExistioAPI,
):
    if command == 'release':
        await release_tag(task_id, data_manager, todoist_api, existio_api)
        return
    elif command == 'update':
        tag = await data_manager.get(task_id)
        if tag:
            await delete_relevant_comment(task_id, todoist_api, include_exist_url=False)
            await post_stats(task_id, tag, todoist_api, existio_api)
        return
    elif command == 'yesterday' or command.startswith(('on:', 'off:')):
        if comment_id:
            await todoist_api.delete_comment(comment_id)
        tag = await data_manager.get(task_id)
        if not tag:
            await answer_command(task_id, f'{EMOJI_FAILED} Tag "{tag}" was not found', comment_id, todoist_api)
            return False
        if command == 'yesterday':
            state = 'on'
            target_date = local_now() - timedelta(days=1)
        elif ':' in command:
            state, target_date = map(str.strip, command.split(':', maxsplit=1))
            if target_date == 'yesterday':
                target_date = local_now() - timedelta(days=1)
            elif target_date == 'today':
                target_date = local_now()
            else:
                try:
                    target_date = date.fromisoformat(target_date)
                except ValueError:
                    await answer_command(task_id, f'{EMOJI_FAILED} Wrong date "{target_date}"', comment_id, todoist_api)
                    return False
        else:
            await answer_command(task_id, f'{EMOJI_FAILED} Wrong command "{command}"', comment_id, todoist_api)
            return

        value = state == 'on'
        await existio_api.attributes_update([
            AttributeValue(name=tag, date=utils.format_date(target_date), value=value),
        ])
        await post_stats(task_id, tag, todoist_api, existio_api)
        return
    tag = command.strip('-').replace(' ', '_')
    if not tag:
        await answer_command(task_id, 'Empty tag name', comment_id, todoist_api)
        return False
    if not tag.startswith('+'):
        await answer_command(task_id, f'Unknown command: "{command}". '
                                      f'Add "+" in the beginning to connect with a tag', comment_id, todoist_api)
        return False
    tag = tag[1:]
    await data_manager.store(task_id, tag)
    await delete_relevant_comment(task_id, todoist_api)
    await todoist_api.add_comment(existio_api.get_tag_url(tag), task_id=task_id)
    await existio_api.attributes_acquire([tag])
    await post_stats(task_id, tag, todoist_api, existio_api)


async def answer_command(
        task_id: str,
        text: str,
        comment_id: str | None,
        todoist_api: TodoistAPIAsync,
):
    if comment_id:
        await todoist_api.add_comment(text, task_id=task_id)
    else:
        await todoist_api.update_task(task_id, description=text)


async def task_updated(
        task: Task,
        data_manager: DataManager,
        todoist_api: TodoistAPIAsync,
        existio_api: ExistioAPI,
):
    task_id = task.id
    tag = await data_manager.get(task_id)
    if not tag:
        return
    description = task.description.strip()
    if not description.startswith('/'):
        return
    command = description[1:]
    result = await process_command(command, task_id, None, data_manager, todoist_api, existio_api)
    if result is not False:
        description = await generate_description(tag, existio_api)
        await todoist_api.update_task(task_id, description=description)


async def task_completed(
        task: Task,
        data_manager: DataManager,
        todoist_api: TodoistAPIAsync,
        existio_api: ExistioAPI,
):
    task_id = task.id
    tag = await data_manager.get(task_id)
    if not tag:
        return
    if task.checked:
        await release_tag(task.id, data_manager, todoist_api, existio_api)
        return
    await existio_api.attributes_update([
        AttributeValue(name=tag, date=current_date()),
    ])
    await post_stats(task_id, tag, todoist_api, existio_api)


async def task_uncompleted(
        task: Task,
        data_manager: DataManager,
        todoist_api: TodoistAPIAsync,
        existio_api: ExistioAPI,
):
    task_id = task.id
    tag = await data_manager.get(task_id)
    if not tag:
        return
    await existio_api.attributes_update([
        AttributeValue(name=tag, date=current_date(), value=0),
    ])
    await post_stats(task_id, tag, todoist_api, existio_api)


async def task_deleted(
        task: Task,
        data_manager: DataManager,
        todoist_api: TodoistAPIAsync,
        existio_api: ExistioAPI,
):
    await release_tag(task.id, data_manager, todoist_api, existio_api)


async def release_tag(
        task_id: str,
        data_manager: DataManager,
        todoist_api: TodoistAPIAsync,
        existio_api: ExistioAPI,
):
    tag = await data_manager.get(task_id)
    if not tag:
        return
    await data_manager.remove(task_id)
    await existio_api.attributes_release([tag])
    await delete_relevant_comment(task_id, todoist_api)


async def delete_relevant_comment(task_id: str, todoist_api: TodoistAPIAsync, include_exist_url=True):
    search = [PREFIX_COMMAND, *EMOJIS]
    if include_exist_url:
        search.append(EXIST_PART_URL)
    comments = await todoist_api.get_comments(task_id=task_id)
    delete_comment_ids = [
        comment.id
        for comment in comments
        if utils.string_contains(comment.content, *search)
    ]
    for comment_id in delete_comment_ids:
        await todoist_api.delete_comment(comment_id)


EVEN_MAP = {
    'note:added': comment_added,
    'item:updated': task_updated,
    'item:completed': task_completed,
    'item:uncompleted': task_uncompleted,
    'item:deleted': task_deleted,
}
