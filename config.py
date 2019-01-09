import logging
import sys

import logbook
import msgpack_numpy
from logbook.compat import RedirectLoggingHandler

IS_PRODUCTION = False

pr0gramm_config = {
    'baseurl': {
        'api': 'https://pr0gramm.com/api',
        'img': 'https://img.pr0gramm.com',
    },
    'username': 'rep0stBot',
    'password': 'wugwLbVs8LDbwlEjwu9c',
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

if IS_PRODUCTION:
    log_handlers = [
        logbook.StreamHandler(sys.stdout, level=logbook.INFO),
        logbook.TimedRotatingFileHandler('logs/rep0st.log', date_format='%d-%m-%Y', bubble=True, level=logbook.DEBUG),
    ]
else:
    log_handlers = [
        logbook.StreamHandler(sys.stdout, level=logbook.DEBUG),
        logbook.TimedRotatingFileHandler('logs/rep0st.log', date_format='%d-%m-%Y', bubble=True, level=logbook.DEBUG),
    ]

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
