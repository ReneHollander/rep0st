from logbook import Logger

import config
from rep0st import util, api
from rep0st.rep0st import get_rep0st

config.load()
log = Logger('tags')

if __name__ == '__main__':
    rep = get_rep0st()

    counter = 0
    for batch in util.batch(10000, api.iterate_tags(start=rep.database.latest_tag_id())):
        session = rep.database.DBSession()
        session.bulk_save_objects(batch)
        session.commit()
        session.close()

    rep.close()
