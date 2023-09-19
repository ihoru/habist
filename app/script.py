import asyncio
import logging
from argparse import ArgumentParser

from todoist_api_python.api_async import TodoistAPIAsync

import tasks
import utils
from config import ENV
from data_manager import DataManager
from existio import ExistioAPI

if not ENV['TODOIST_API_KEY']:
    utils.error("TODOIST_API_KEY should not be empty")
if not ENV['EXISTIO_API_KEY']:
    utils.error("EXISTIO_API_KEY should not be empty")

logging_format = '%(asctime)s %(levelname)s:%(name)s %(filename)s:%(lineno)d %(funcName)s - %(message)s'
if ENV['DEBUG']:
    logging.basicConfig(level=logging.DEBUG, format=logging_format)
else:
    logging.basicConfig(format=logging_format)

todoist_api = TodoistAPIAsync(ENV['TODOIST_API_KEY'])
existio_api = ExistioAPI(ENV['EXISTIO_API_KEY'])
data_manager = DataManager(ENV['DATA_FILENAME'])


async def update_task_stats(task_id, tag, update_months: int):
    try:
        logging.info(f'starting {task_id = }, {tag = }')
        texts = await tasks.post_stats(task_id, tag, todoist_api, existio_api, update_months=update_months)
        logging.info(f'finished {task_id = }, {tag = }')
    except Exception as e:
        logging.warning(f'FAILURE: {task_id = }, {tag = }')
        if ENV['DEBUG']:
            raise
        logging.error(e)
    else:
        logging.info(f'SUCCESS: {task_id = }, {tag = }')
        logging.debug('Stats:\n%s\n', '--\n'.join(texts))


async def process_one_task(task_id: str, force: bool, update_months: int):
    data = await data_manager.all()
    tag = data[task_id]
    if force:
        await tasks.delete_relevant_comment(task_id, todoist_api, include_exist_url=False)
    await update_task_stats(task_id, tag, update_months)
    return 'ok'


async def process_all_tasks(force: bool, update_months: int):
    data = await data_manager.all()
    if force:
        # delete all relevant comments first
        await asyncio.gather(*[
            tasks.delete_relevant_comment(task_id, todoist_api, include_exist_url=False)
            for task_id in data.keys()
        ])
    await asyncio.gather(*[
        update_task_stats(task_id, tag, update_months)
        for task_id, tag in data.items()
    ])
    return 'ok'


def main():
    parser = ArgumentParser()
    parser.add_argument('action', choices=['update_all', 'update_task'], help='Which action to perform')
    parser.add_argument('--force', action='store_true', help='Force update all months')
    known_args = parser.parse_known_args()[0]

    parser.add_argument('--update-months', '-m', help='How many months to process', type=int,
                        default=12 if known_args.force else None)
    if known_args.action == 'update_task':
        parser.add_argument('task_id', type=int, help='Which task to update (only for action=update_task)')
    args = parser.parse_args()

    if args.action == 'update_all':
        # This will start update in parallel (10x speed increase)
        asyncio.run(process_all_tasks(args.force, args.update_months))
    elif args.action == 'update_task':
        assert args.task_id, 'task_id should not be empty'
        asyncio.run(process_one_task(str(args.task_id), args.force, args.update_months))


if __name__ == '__main__':
    main()
