import sys

import redis
from logbook import StreamHandler, Logger
from sqlalchemy import create_engine

import api
import util
from rep0st import rep0st

StreamHandler(sys.stdout).push_application()
log = Logger('APP')

rep = rep0st(
    create_engine('mysql+cymysql://rep0st:rep0stpw@localhost/rep0st?charset=utf8'),
    redis.StrictRedis(host='localhost', port=6379, db=0),
    "/media/pr0gramm/images")

counter = 0
for batch in util.batch(10000, api.iterate_tags(start=rep.database.latest_tag_id())):
    rep.database.session.bulk_save_objects(batch)
    rep.database.get_session().commit()

rep.close()
