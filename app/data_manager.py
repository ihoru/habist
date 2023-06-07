import aiofiles
from aiofiles import ospath


class DataManager:
    _filename = None
    _data: dict = None

    def __init__(self, filename):
        self._filename = filename

    async def _load(self):
        self._data = dict()
        file_exists = await ospath.exists(self._filename)
        if not file_exists:
            return
        async with aiofiles.open(self._filename, 'r') as f:
            lines = await f.readlines()
            for line in lines:
                r = line.strip().split(':', maxsplit=1)
                if len(r) == 2:
                    task_id, tag = r
                    self._data[task_id] = tag

    async def _save(self):
        lines = [
            f'{task_id}:{tag}'
            for task_id, tag in self._data.items()
        ]
        async with aiofiles.open(self._filename, 'w') as f:
            await f.write('\n'.join(lines))

    async def get(self, task_id: str):
        if self._data is None:
            await self._load()
        return self._data.get(task_id)

    async def store(self, task_id: str, tag: str):
        if self._data is None:
            await self._load()
        self._data[task_id] = tag
        await self._save()

    async def remove(self, task_id: str):
        if self._data is None:
            await self._load()
        if task_id in self._data:
            del self._data[task_id]
            await self._save()

    async def all(self):
        if self._data is None:
            await self._load()
        return self._data.copy()
