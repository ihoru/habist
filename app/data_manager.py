import os.path


class DataManager:
    _filename = None
    _data: dict = None

    def __init__(self, filename):
        self._filename = filename

    def _load(self):
        if self._data is not None:
            return
        lines = []
        if os.path.exists(self._filename):
            with open(self._filename, 'r') as f:
                lines = f.readlines()
        self._data = dict()
        for line in lines:
            r = line.strip().split(':', maxsplit=1)
            if len(r) == 2:
                task_id, tag = r
                self._data[task_id] = tag

    def _save(self):
        lines = [
            f'{task_id}:{tag}'
            for task_id, tag in self._data.items()
        ]
        with open(self._filename, 'w') as f:
            f.write('\n'.join(lines))

    def get(self, task_id: str):
        self._load()
        return self._data.get(task_id)

    def store(self, task_id: str, tag: str):
        self._load()
        self._data[task_id] = tag
        self._save()

    def remove(self, task_id: str):
        self._load()
        if task_id in self._data:
            del self._data[task_id]
        self._save()

    def all(self):
        self._load()
        return self._data.copy()
