import sys


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
