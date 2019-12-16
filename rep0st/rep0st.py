import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import time

import cv2
import numpy as np
import redis
from cv2 import imread, imdecode
from logbook import Logger
from requests import HTTPError
from sqlalchemy import create_engine

import config
from rep0st.analyze import analyze_image
from rep0st.api import iterate_posts, download_image
from rep0st.database import Database, PostStatus, Feature
from rep0st.index import Rep0stIndex
from rep0st.util import batched_pool_runner, batch

config.load()
log = Logger('rep0st')
rep0st_instance = None


def get_rep0st():
    global rep0st_instance
    if rep0st_instance is None:
        rep0st_instance = rep0st(
            create_engine(
                'mysql+cymysql://' + config.mysql_config['user'] + ':' + config.mysql_config['password'] + '@' +
                config.mysql_config['host'] + '/' + config.mysql_config['database'] + '?charset=utf8'),
            redis.StrictRedis(host=config.redis_config['host'], port=config.redis_config['port'],
                              db=config.redis_config['database']),
            config.image_config['path'])
    return rep0st_instance


class rep0st():
    def __init__(self, db_engine, redis, imgdir):
        self.database = Database(db_engine)
        self.redis = redis
        self.imgdir = Path(imgdir)
        self.index = None
        if not self.imgdir.is_dir():
            raise FileNotFoundError("invalid image directory")

    def update_database(self):
        id = self.database.latest_post_id()
        log.info("starting database update. latest post {}", id)
        session = self.database.DBSession()
        counter = 0
        for b in batch(1000, iterate_posts(id)):
            counter += len(b)
            session.bulk_save_objects(b)

        session.commit()
        session.close()
        log.info("finished database update. added {} posts to database", counter)

    def update_features(self):
        log.info("started updating features")

        def work(post):
            return self.analyze_post(post)

        pool = ThreadPoolExecutor(max_workers=16)

        cnt = 0

        total_count = self.database.get_posts_missing_features().count()
        start = time()

        session = self.database.DBSession()

        bs = 500

        for result in batched_pool_runner(work, self.database.get_posts_missing_features().yield_per(1000), pool, bs):
            if result.result() is not None:
                post, features = result.result()
                post.status = PostStatus.INDEXED

                for type, data in features.items():
                    session.merge(Feature.from_analyzeresult(post, type, data))

            cnt += 1
            if cnt % bs == 0:
                session.commit()

                stop = time()
                left = total_count - cnt
                last_time = (stop - start) / bs * 1000
                log.debug("Processed {}/{} images. Time per image: {}ms. Estimated time: {}", cnt, total_count,
                          "{0:.2f}".format(last_time), str(datetime.timedelta(seconds=last_time / 1000 * left)))

                start = time()

        session.commit()
        session.close()

        log.info("finished updating features. calculated {} new features", cnt)

    def read_image(self, post):
        return read_image(self.imgdir, self.database, post)

    def analyze_post(self, post):
        image = self.read_image(post)
        if image is None:
            return None
        else:
            result = analyze_image(image)
            return post, result

    def get_index(self):
        if self.index is None:
            self.index = Rep0stIndex(self)
        return self.index

    def close(self):
        if self.index:
            self.index.close()
        self.database.close()

    def get_statistics(self):
        index_id = self.index.current_index if self.index else -1
        return {
            'index': {
                'current': index_id,
                'latest_post': self.database.latest_post_id(),
                'last_annoy_update': datetime.datetime.now(),
                'last_redis_update': datetime.datetime.now(),
            },
            'user': {
                'last_hour': 10,
                'last_day': 100,
                'total': 10000,
            }
        }

    def download_post_media(self, post):
        try:
            img_file = Path(self.imgdir) / post.image
            if img_file.is_file():
                return
            data = download_image(post)
            with img_file.open("wb") as f:
                f.write(data)
        except:
            log.exception("marking post {} as broken, because downloading image \"{}\" caused an error", post, post.image)
            post.status = PostStatus.BROKEN


def read_image(imgdir, database, post):
    try:
        img_file = Path(imgdir) / post.image
        if img_file.is_file():
            image = imread(str(img_file), cv2.IMREAD_COLOR)
        else:
            parent = img_file.parent
            if not parent.exists():
                parent.mkdir(parents=True)

            data = download_image(post)
            with img_file.open("wb") as f:
                f.write(data)
            image = imdecode(np.asarray(bytearray(data), dtype=np.uint8), cv2.IMREAD_COLOR)
    except HTTPError as e:
        if e.response.status_code == 404:
            log.exception("marking post {} as broken, because the image \"{}\" was not found on the server", post, post.image)
            post.status = PostStatus.BROKEN
            return None
        else:
            raise e
    except:
        log.exception("marking post {} as broken, because the image \"{}\" is invalid", post, post.image)
        post.status = PostStatus.BROKEN
        return None

    if image is None:
        log.info("marking post {} as broken, because the image \"{}\" is invalid", post, post.image)
        post.status = PostStatus.BROKEN
        return None
    else:
        return image
