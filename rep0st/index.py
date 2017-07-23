from collections import namedtuple
from time import time

import msgpack
import numpy as np
from annoy import AnnoyIndex
from logbook import Logger

import config
from rep0st.analyze import analyze_image
from rep0st.database import FeatureType
from rep0st.util import SimplePriorityQueue, dist

log = Logger('index')

SearchResult = namedtuple('SearchResult', 'post, similarity')


class Rep0stIndex:
    def __init__(self, rep0st):
        self.rep0st = rep0st
        self.p = rep0st.redis.pubsub()
        self.p.subscribe(**{'rep0st-index-change': self.index_change_handler})
        self.listenthread = self.p.run_in_thread(sleep_time=0.001)
        self.current_index = int(self.rep0st.redis.get('rep0st-current-index'))
        self.annoy_index = None
        self.load_index(self.current_index)

    def index_change_handler(self, message):
        next_index = int(message['data'])
        log.info("recieved index update. new index: {}", next_index)
        self.load_index(next_index)

    def load_index(self, index_id):
        if self.annoy_index is None:
            log.info("loading initial index with id {}", self.current_index)
        else:
            log.info("switching index from {} to {}", self.current_index, index_id)

        newindex = AnnoyIndex(108, metric='euclidean')
        newindex.load('index_' + str(index_id) + '.ann')
        if self.annoy_index is not None:
            self.annoy_index.unload()
        self.annoy_index = newindex
        self.current_index = index_id
        log.info("finished switching index. now using index {}", self.current_index)

    def search(self, image, k=-1):
        start = time()

        if k == -1:
            k = config.index_config['default_k']

        nearest = SimplePriorityQueue(k)

        fv = analyze_image(image)[FeatureType.FEATURE_VECTOR]
        arr = np.asarray(bytearray(fv)).astype(np.float32)

        annoy_results = self.annoy_index.get_nns_by_vector(arr, k, search_k=config.index_config['search_k'],
                                                           include_distances=True)

        for i in range(0, len(annoy_results[0])):
            a_p = annoy_results[1][i]
            a_v = annoy_results[0][i]
            nearest.add(a_p, a_v)

        for element in self.rep0st.redis.lrange('rep0st-latest-feature-vectors-index-' + str(self.current_index), 0,
                                                -1):
            element = msgpack.unpackb(element)
            data = np.asarray(bytearray(element['data'])).astype(np.float32)
            distance = dist(arr, data)
            nearest.add(distance, element['id'])

        list = []
        for item in nearest:
            post = self.rep0st.database.get_post_by_id(item.value)
            list.append(SearchResult(post, item.priority))

        stop = time()

        log.debug("query with search_k={} and {} trees took {}ms", config.index_config['search_k'],
                  config.index_config['tree_count'], str((stop - start) * 1000))

        return list

    def close(self):
        self.listenthread.stop()
        self.p.close()
