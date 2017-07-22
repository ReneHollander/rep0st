import sys

import msgpack_numpy
import redis
from logbook import StreamHandler, TimedRotatingFileHandler
from sqlalchemy import create_engine

from rep0st import rep0st

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
    'search_k': 5000,
    'tree_count': 20,
    'default_k': 20,
}

image_config = {
    'path': '/media/pr0gramm/images',
}

log_config = [
    StreamHandler(sys.stdout),
    TimedRotatingFileHandler('logs/rep0st.log', date_format='%d-%m-%Y', bubble=True),
]


def create_rep0st():
    return rep0st(
        create_engine('mysql+cymysql://' + mysql_config['user'] + ':' + mysql_config['password'] + '@' +
                      mysql_config['host'] + '/' + mysql_config['database'] + '?charset=utf8'),
        redis.StrictRedis(host=redis_config['host'], port=redis_config['port'], db=redis_config['database']),
        image_config['path'])


is_loaded = False


def load():
    global is_loaded
    if not is_loaded:
        msgpack_numpy.patch()
        for handler in log_config:
            handler.push_application()
        is_loaded = True


load()
