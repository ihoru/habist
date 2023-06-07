import sys
from collections import OrderedDict


class OrderedDefaultDict(OrderedDict):
    def __init__(self, default_factory=None, *args, **kwargs):
        if default_factory is not None and not hasattr(default_factory, '__call__'):
            raise TypeError('first argument must be callable')
        OrderedDict.__init__(self, *args, **kwargs)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    def __repr__(self):
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory, OrderedDict.__repr__(self))


def error(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)
    exit(1)


def my_bool(v, strict=False):
    v = str(v).lower()
    if strict:
        return v in ('true', '1')
    if v in ('false', '0'):
        return False
    return bool(v)


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]
