from logbook import Logger

import config
from rep0st import util, api

log = Logger('APP')

if __name__ == '__main__':
    rep = config.get_rep0st()

    counter = 0
    for batch in util.batch(10000, api.iterate_tags(start=rep.database.latest_tag_id())):
        rep.database.session.bulk_save_objects(batch)
        rep.database.get_session().commit()

    rep.close()
