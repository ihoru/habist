import os

from dotenv import dotenv_values

import utils

__all__ = [
    'ENV',
]

ENV = {
    **dotenv_values('.env.example'),
    **dotenv_values('.env'),
    **os.environ,
}

# process booleans
for key in [
    'DEBUG',
]:
    ENV[key] = utils.my_bool(ENV[key])
