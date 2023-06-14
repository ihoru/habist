import base64
import hashlib
import hmac
import logging
from typing import Annotated

from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Header
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ErrorWrapper
from starlette.requests import Request
from todoist_api_python.api_async import TodoistAPIAsync

import tasks
import todoist
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

app = FastAPI(
    debug=ENV['DEBUG'],
)

todoist_api = TodoistAPIAsync(ENV['TODOIST_API_KEY'])
existio_api = ExistioAPI(ENV['EXISTIO_API_KEY'])
data_manager = DataManager(ENV['DATA_FILENAME'])


@app.get('/')
async def root():
    return 'Hey there!'


@app.get('/acquired_tags/')
async def acquired_tags(
        authorization: Annotated[str, Header()],
):
    if authorization.lower() != f"token {ENV['ACQUIRED_TAGS_TOKEN']}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect Authorization token header')
    data = await data_manager.all()
    return list(data.values())


@app.post('/todoist/')
async def todoist_webhook(
        request: Request,
        webhook: todoist.Webhook,
        background_tasks: BackgroundTasks,
        todoist_hmac_sha256: str = Header(default=None, alias='X-Todoist-HMAC-SHA256'),
):
    if not ENV['DEBUG']:
        if not todoist_hmac_sha256:
            raise HTTPException(status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
                                detail=f'Empty X-Todoist-HMAC-SHA256 header')
        calculated_hmac = base64.b64encode(hmac.new(
            ENV['TODOIST_CLIENT_SECRET'].encode(),
            msg=await request.body(),
            digestmod=hashlib.sha256,
        ).digest()).decode()
        if todoist_hmac_sha256 != calculated_hmac:
            raise HTTPException(status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
                                detail='Incorrect X-Todoist-HMAC-SHA256 header')
    if webhook.event_name not in tasks.EVEN_MAP:
        raise RequestValidationError([ErrorWrapper(ValueError('Unknown event'), ('body', 'event_name'))])
    if not (
            (webhook.event_name.startswith('note:') and webhook.initiator.id == webhook.event_data.item.user_id)
            or
            (webhook.event_name.startswith('item:') and webhook.initiator.id == webhook.event_data.user_id)
    ):
        return 'Incorrect ownership, but I do not care'
    logging.info('Todoist.webhook: event_name=%s, event_data.id=%s', webhook.event_name, webhook.event_data.id)
    logging.debug('Todoist.webhook: event_data=%r', webhook.event_data)
    background_tasks.add_task(
        tasks.EVEN_MAP[webhook.event_name],
        webhook.event_data,
        data_manager,
        todoist_api,
        existio_api,
    )
    return 'ok'


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    logging.warning('%r', exc)
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.info('%r', exc)
    return await request_validation_exception_handler(request, exc)
