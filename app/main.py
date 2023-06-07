import logging

from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from todoist_api_python.api_async import TodoistAPIAsync

import tasks
import todoist
import utils
from config import ENV
from data_manager import DataManager
from existio import ExistioAPI

if not ENV['TODOIST_API_KEY']:
    utils.error("TODOIST_API_KEY should not be empty")

logging_format = '%(asctime)s %(levelname)s:%(name)s %(filename)s:%(lineno)d %(funcName)s - %(message)s'
if ENV['DEBUG']:
    logging.basicConfig(level=logging.DEBUG, format=logging_format)
else:
    logging.basicConfig(format=logging_format)

app = FastAPI(
    debug=ENV['DEBUG'],
)

todoist_api = TodoistAPIAsync(ENV['TODOIST_API_KEY'])
existio_api = ExistioAPI(ENV['EXISTIO_API_KEY'])
data_manager = DataManager(ENV['DATA_FILENAME'])


@app.get('/')
async def root():
    return 'Hey there!'


@app.post('/todoist/')
async def todoist_webhook(webhook: todoist.Webhook, background_tasks: BackgroundTasks):
    # TODO: check X-Todoist-Hmac-SHA256: UEEq9si3Vf9yRSrLthbpazbb69kP9+CZQ7fXmVyjhPs=
    if webhook.version != todoist.API_VERSION:
        logging.warning('Todoist.webhook: wrong version (%s)', webhook.version)
        raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail=f'Expecting version = {todoist.API_VERSION}')
    if webhook.event_name not in tasks.EVEN_MAP:
        logging.warning('Todoist.webhook: unknown even_name (%s)', webhook.event_name)
        raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail='Unknown event_name')
    if not (
            (webhook.event_name.startswith('note:') and webhook.initiator.id == webhook.event_data.item.user_id)
            or
            (webhook.event_name.startswith('item:') and webhook.initiator.id == webhook.event_data.user_id)
    ):
        raise HTTPException(status.HTTP_200_OK, detail='Incorrect ownership')
    logging.debug('Todoist.webhook: event_name=%s event_data=%r', webhook.event_name, webhook.event_data)
    background_tasks.add_task(
        tasks.EVEN_MAP[webhook.event_name],
        webhook.event_data,
        data_manager,
        todoist_api,
        existio_api,
    )
    return 'ok'
