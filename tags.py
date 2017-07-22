from logbook import Logger

import api
import config
import util

log = Logger('APP')

rep = config.create_rep0st()

counter = 0
for batch in util.batch(10000, api.iterate_tags(start=rep.database.latest_tag_id())):
    rep.database.session.bulk_save_objects(batch)
    rep.database.get_session().commit()

rep.close()
