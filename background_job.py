import datetime
import sys
import time

import msgpack
import msgpack_numpy
import numpy as np
import redis
import schedule
from annoy import AnnoyIndex
from logbook import Logger, StreamHandler
from sqlalchemy import create_engine

import analyze
import api
from database import PostStatus, Feature, FeatureType, PostType
from rep0st import rep0st

StreamHandler(sys.stdout).push_application()
log = Logger('background-job')

msgpack_numpy.patch()

rep = rep0st(
    create_engine('mysql+cymysql://rep0st:rep0stpw@localhost/rep0st?charset=utf8'),
    redis.StrictRedis(host='localhost', port=6379, db=0),
    "/media/pr0gramm/images")

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
        rep.database.get_session().add(post)
        if post.type == PostType.IMAGE:
            image = rep.read_image(post)
            if image is not None:
                result = analyze.analyze_image(image)
                post.status = PostStatus.INDEXED

                for type, data in result.items():
                    rep.database.session.merge(Feature.from_analyzeresult(post, type, data))
                    if type == FeatureType.FEATURE_VECTOR:
                        features_FEATURE_VECTOR.append(msgpack.packb({
                            'id': post.id,
                            'data': data
                        }))

        rep.database.get_session().commit()
    if len(features_FEATURE_VECTOR) > 0:
        rep.redis.lpush('rep0st-latest-feature-vectors-index-' + str(index_id), *features_FEATURE_VECTOR)

    log.info("finished getting new posts. added {} posts to database", counter)


def build_index(index_id):
    n_trees = 20

    log.info("started index build")
    count = rep.database.session.query(Feature).filter(Feature.type == FeatureType.FEATURE_VECTOR).count()
    index = AnnoyIndex(108, metric='euclidean')
    cnt = 0
    log.info("adding {} features to index", count)
    start = time.time()
    for feature in rep.database.session.query(Feature).filter(Feature.type == FeatureType.FEATURE_VECTOR).yield_per(
            1000):
        arr = np.asarray(bytearray(feature.data)).astype(np.float32)
        index.add_item(feature.post_id, arr)
        cnt += 1
        if cnt % 10000 == 0:
            log.debug("added {}/{} features to the index", cnt, count)
    stop = time.time()
    log.info("added all {} features to the index in {}", count, str(datetime.timedelta(seconds=stop - start)))
    log.info("building index with {} trees. this will take a while...", n_trees)
    start = time.time()
    index.build(20)
    index_file = "index_" + str(index_id) + ".ann"
    log.info("saving index to file {}", index_file)
    index.save(index_file)
    stop = time.time()

    log.debug("finished building of index. it took {}", str(datetime.timedelta(seconds=stop - start)))


def job_build_index():
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


def job_update():
    update(current_index)


if __name__ == '__main__':
    if rep.redis.exists('rep0st-current-index'):
        current_index = int(rep.redis.get('rep0st-current-index'))
        print(type(current_index))
        log.info("reusing index id {} for cycling", current_index)
    else:
        current_index = 2
        log.info("starting fresh index cycle with id 1", current_index)

    job_build_index()

    # schedule.every().day.at("03:00").do(job_build_index)
    schedule.every(5).minutes.do(job_build_index)
    schedule.every(1).minutes.do(job_update)

    while True:
        schedule.run_pending()
        time.sleep(1)
