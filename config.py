import logging
import sys

import logbook
import msgpack_numpy
import redis
from logbook.compat import RedirectLoggingHandler
from sqlalchemy import create_engine

from rep0st.rep0st import rep0st

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
    'search_k': 10000,
    'tree_count': 20,
    'default_k': 25,
}

image_config = {
    'path': '/media/pr0gramm/images',
}

backgroundjob_config = {
    'dev_mode': True,
    'rebuild_index_time': '03:00',
    'update_index_every_seconds': 60,
}

log_handlers = [
    logbook.StreamHandler(sys.stdout, level=logbook.INFO),
    logbook.TimedRotatingFileHandler('logs/rep0st.log', date_format='%d-%m-%Y', bubble=True, level=logbook.DEBUG),
]

rep0st_instance = None


def get_rep0st():
    global rep0st_instance
    if rep0st_instance is None:
        rep0st_instance = rep0st(
            create_engine('mysql+cymysql://' + mysql_config['user'] + ':' + mysql_config['password'] + '@' +
                          mysql_config['host'] + '/' + mysql_config['database'] + '?charset=utf8'),
            redis.StrictRedis(host=redis_config['host'], port=redis_config['port'], db=redis_config['database']),
            image_config['path'])
    return rep0st_instance


is_loaded = False


def load():
    global is_loaded
    if not is_loaded:
        # Patch numpy types into msgpack
        msgpack_numpy.patch()

        # Redirect flask logger to logbook
        werkzeug_logger = logging.getLogger('werkzeug')
        del werkzeug_logger.handlers[:]
        werkzeug_logger.addHandler(RedirectLoggingHandler())

        # Override the built-in werkzeug logging function in order to change the log line format.
        from werkzeug.serving import WSGIRequestHandler
        WSGIRequestHandler.log = lambda self, type, message, *args: getattr(werkzeug_logger, 'debug')(
            '%s %s' % (self.address_string(), message % args))

        # Register loggers
        for handler in log_handlers:
            handler.push_application()
        is_loaded = True


load()
