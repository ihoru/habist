from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from todoist_api_python.api_async import TodoistAPIAsync

import tasks
import todoist
import utils
from config import ENV

if not ENV['TODOIST_API_KEY']:
    utils.error("TODOIST_API_KEY should not be empty")

app = FastAPI(
    debug=ENV['DEBUG'],
)

TodoistAPI = TodoistAPIAsync(ENV['TODOIST_API_KEY'])


@app.get('/')
async def root():
    return 'Hey there!'


@app.post('/todoist/')
async def todoist_webhook(webhook: todoist.Webhook, background_tasks: BackgroundTasks):
    # TODO: check X-Todoist-Hmac-SHA256: UEEq9si3Vf9yRSrLthbpazbb69kP9+CZQ7fXmVyjhPs=
    if webhook.version != todoist.API_VERSION:
        raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail=f'Expecting version = {todoist.API_VERSION}')
    if webhook.event_name == 'note:added':
        background_tasks.add_task(tasks.comment_added, webhook.event_data)
    elif webhook.event_name == 'item:completed':
        background_tasks.add_task(tasks.task_completed, webhook.event_data)
    elif webhook.event_name == 'item:uncompleted':
        background_tasks.add_task(tasks.task_uncompleted, webhook.event_data)
    else:
        raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail='Unknown event_name')
    return 'ok'
