import datetime
import time

import msgpack
import numpy as np
import schedule
from annoy import AnnoyIndex
from logbook import Logger

import config
from rep0st import api, analyze
from rep0st.database import PostStatus, Feature, FeatureType, PostType
from rep0st.rep0st import get_rep0st

config.load()
log = Logger('background-job')
rep = get_rep0st()
current_index = 1


def update(index_id):
    latest_id = rep.database.latest_post_id()
    log.info("getting new posts. latest post {}", latest_id)
    counter = 0

    posts = []
    ids = []
    features_FEATURE_VECTOR = []
    for post in api.iterate_posts(latest_id):
        counter += 1
        posts.append(post)
        ids.append(post.id)
        session = rep.database.DBSession()
        session.add(post)
        if post.type == PostType.IMAGE:
            image = rep.read_image(post)
            if image is not None:
                result = analyze.analyze_image(image)
                post.status = PostStatus.INDEXED

                for type, data in result.items():
                    session.merge(Feature.from_analyzeresult(post, type, data))
                    if type == FeatureType.FEATURE_VECTOR:
                        features_FEATURE_VECTOR.append(msgpack.packb({
                            'id': post.id,
                            'data': data
                        }))
        else:
            rep.download_post_media(post)

        session.commit()
        session.close()
    if len(features_FEATURE_VECTOR) > 0:
        rep.redis.lpush('rep0st-latest-feature-vectors-index-' + str(index_id), *features_FEATURE_VECTOR)

    log.info("finished getting new posts. added {} posts to database", counter)


def build_index(index_id):
    n_trees = config.index_config['tree_count']

    log.info("started index build")
    session = rep.database.DBSession()
    count = session.query(Feature).filter(Feature.type == FeatureType.FEATURE_VECTOR).count()
    index = AnnoyIndex(108, metric='euclidean')
    cnt = 0
    log.info("adding {} features to index", count)
    start = time.time()
    for feature in session.query(Feature).filter(Feature.type == FeatureType.FEATURE_VECTOR).yield_per(1000):
        arr = np.asarray(bytearray(feature.data)).astype(np.float32)
        index.add_item(feature.post_id, arr)
        cnt += 1
        if cnt % 10000 == 0:
            log.debug("added {}/{} features to the index", cnt, count)
    session.close()
    stop = time.time()
    log.info("added all {} features to the index in {}", count, str(datetime.timedelta(seconds=stop - start)))
    log.info("building index with {} trees. this will take a while...", n_trees)
    start = time.time()
    index.build(20)
    index_file = config.index_config['index_path'] + "index_" + str(index_id) + ".ann"
    log.info("saving index to file {}", index_file)
    index.save(index_file)
    stop = time.time()

    log.debug("finished building of index. it took {}", str(datetime.timedelta(seconds=stop - start)))


def job_build_index():
    try:
        global current_index
        next_index = 2 if current_index == 1 else 1
        log.info("current index is {}, next will be {}", current_index, next_index)
        rep.update_database()
        rep.update_features()
        build_index(next_index)
        rep.redis.delete('rep0st-latest-feature-vectors-index-' + str(next_index))
        rep.redis.set('rep0st-current-index', next_index)
        rep.redis.publish('rep0st-index-change', next_index)
        current_index = next_index
    except:
        log.error('Error executing job_build_index', exc_info=True)


def job_update():
    try:
        update(current_index)
    except:
        log.error('Error executing job_update', exc_info=True)


if __name__ == '__main__':
    if rep.redis.exists('rep0st-current-index'):
        current_index = int(rep.redis.get('rep0st-current-index'))
        log.info("reusing index id {} for cycling", current_index)
    else:
        current_index = 2
        log.info("starting fresh index cycle with id 1", current_index)

    job_build_index()

    if config.IS_PRODUCTION:
        schedule.every().day.at(config.backgroundjob_config['rebuild_index_time']).do(job_build_index)
    else:
        schedule.every(5).minutes.do(job_build_index)
    schedule.every(config.backgroundjob_config['update_index_every_seconds']).seconds.do(job_update)

    while True:
        schedule.run_pending()
        time.sleep(1)
