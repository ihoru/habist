import asyncio
import logging

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


async def process_task(task_id, tag):
    try:
        print(f'starting {task_id = }, {tag = }')
        stats = await tasks.post_stats(task_id, tag, existio_api, todoist_api)
        print(f'finished {task_id = }, {tag = }')
    except Exception as e:
        logging.warning('FAILURE: task ID %s, tag: "%s"', task_id, tag)
        logging.error(e)
    else:
        logging.info('SUCCESS: task ID: %s, tag: "%s"', task_id, tag)
        logging.debug('Stats:\n%s', stats)


async def main():
    data = await data_manager.all()
    # Uncomment if it's needed to run each task one by one
    # for task_id, tag in data.items():
    #     await process_task(task_id, tag)

    # This will start update in parallel (10x speed increase)
    await asyncio.gather(*[
        process_task(task_id, tag)
        for task_id, tag in data.items()
    ])
    return 'ok'


if __name__ == '__main__':
    asyncio.run(main())
