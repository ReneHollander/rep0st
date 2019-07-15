import sys

import msgpack_numpy
import logbook

IS_PRODUCTION = False

pr0gramm_config = {
    'baseurl': {
        'api': 'https://pr0gramm.com/api',
        'img': 'https://img.pr0gramm.com',
    },
    'username': 'USERNAME',
    'password': 'PASSWORD',
}

mysql_config = {
    'user': 'rep0st',
    'password': 'rep0stpw',
    'host': 'localhost',
    'database': 'rep0st',
}

redis_config = {
    'host': 'localhost',
    'port': 6379,
    'database': 0,
}

index_config = {
    'index_path': './',
    'search_k': 10000,
    'tree_count': 20,
    'default_k': 25,
}

image_config = {
    'path': '/media/pr0gramm/images',
}

backgroundjob_config = {
    'rebuild_index_time': '03:00',
    'update_index_every_seconds': 60,
}

is_loaded = False


def load():
    global is_loaded
    if not is_loaded:
        # Patch numpy types into msgpack
        msgpack_numpy.patch()

        logbook.StreamHandler(sys.stdout, level=logbook.DEBUG).push_application()
        logbook.compat.redirect_logging()
        is_loaded = True


load()
