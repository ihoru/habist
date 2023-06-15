import logging
from datetime import date
from operator import methodcaller
from typing import List, NamedTuple

import aiohttp

__all__ = [
    'AttributeValue',
    'ExistioAPI',
]

import utils

logger = logging.getLogger(__name__)


class AttributeValue(NamedTuple):
    name: str
    date: str
    value: int = 1


class ExistioAPI:
    API_VERSION = 2
    BASE_URL = f'https://exist.io/api/{API_VERSION}/'
    TAG_URL = 'https://exist.io/data/trends/custom/{}'

    LIMIT_MAXIMUM_OBJECTS_PER_REQUEST = 35
    LIMIT_MAXIMUM_DAYS = 31
    LIMIT_MAXIMUM_LIMIT = 100

    _token: str

    def __init__(self, token):
        self._token = token

    async def _request(self, method, path, **kwargs):
        method = method.upper()
        path = path.lstrip('/')
        url = self.BASE_URL + path
        kwargs.setdefault('headers', dict(Authorization=f'Bearer {self._token}'))
        logger.debug(f'request {method} {url}')
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                logger.debug(f'status: {response.status}')
                result = await response.json()
        detail = result.get('detail')
        if detail:
            logger.error(f'error with detail: {detail} in request "{path}"')
        failed = result.get('failed')
        if failed:
            logger.error(f'failed: {failed} in request "{path}"')
        return result

    async def get(self, path, params=None, **kwargs):
        return await self._request('get', path, params=params, **kwargs)

    async def post(self, path, json=None, **kwargs):
        return await self._request('post', path, json=json, **kwargs)

    async def attribute_values(self, name, date_min: date, date_max: date) -> dict[date, int]:
        assert (date_max - date_min).days <= self.LIMIT_MAXIMUM_LIMIT, \
            f'date_max - date_min must be less than {self.LIMIT_MAXIMUM_LIMIT} days'
        params = dict(
            attribute=name,
            limit=self.LIMIT_MAXIMUM_LIMIT,
            date_min=date_min.strftime('%Y-%m-%d'),
            date_max=date_max.strftime('%Y-%m-%d'),
        )
        result = await self.get('/attributes/values/', params=params)
        return dict(
            (date.fromisoformat(item['date']), int(item['value']))
            for item in result.get('results') or []
            if item['value'] and item['value'] > 0
        )

    async def attributes_acquire(self, names):
        logging.debug(f'acquire {len(names)} tags: {names}')
        failed = []
        for chunk in utils.chunks(names, self.LIMIT_MAXIMUM_OBJECTS_PER_REQUEST):
            result = await self.post('/attributes/acquire/', json=[
                dict(name=name)
                for name in chunk
            ])
            failed.extend(result.get('failed') or [])
        if not failed:
            return
        create_tags = []
        for element in failed:
            if element['error_code'] == 'not_found':
                create_tags.append(element['name'])
        if not create_tags:
            return
        logging.debug(f'creating {len(create_tags)} tags: {create_tags}')
        await self.attributes_create(create_tags)

    async def attributes_release(self, names):
        logging.debug(f'release {len(names)} tags: {names}')
        for chunk in utils.chunks(names, self.LIMIT_MAXIMUM_OBJECTS_PER_REQUEST):
            await self.post('/attributes/release/', json=[
                dict(name=name)
                for name in chunk
            ])

    async def attributes_create(self, names):
        for chunk in utils.chunks(names, self.LIMIT_MAXIMUM_OBJECTS_PER_REQUEST):
            await self.post('/attributes/create/', json=[
                dict(
                    name=name,
                    label=name.replace('_', ' '),
                    group='custom',
                    manual=True,
                    value_type=7,  # boolean (the only option available for custom attributes)
                )
                for name in chunk
            ])

    async def attributes_update(self, data: List[AttributeValue]):
        await self.attributes_acquire([item.name for item in data])
        for chunk in utils.chunks(data, self.LIMIT_MAXIMUM_OBJECTS_PER_REQUEST):
            await self.post('/attributes/update/', json=list(map(methodcaller('_asdict'), chunk)))

    @classmethod
    def get_tag_url(cls, tag):
        return cls.TAG_URL.format(tag)
