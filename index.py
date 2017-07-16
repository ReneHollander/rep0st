from collections import namedtuple
from logging import Logger

import msgpack
import msgpack_numpy
import numpy as np
from annoy import AnnoyIndex

from analyze import analyze_image
from database import FeatureType
from util import SimplePriorityQueue, dist

msgpack_numpy.patch()

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
        print(message)

    def load_index(self, index_id):
        if self.annoy_index is not None:
            self.annoy_index.unload()

        newindex = AnnoyIndex(108, metric='euclidean')
        newindex.load('index_' + str(index_id) + '.ann')
        self.annoy_index = newindex
        self.current_index = index_id

    def search(self, image, k=20):
        nearest = SimplePriorityQueue(k)

        fv = analyze_image(image)[FeatureType.FEATURE_VECTOR]
        arr = np.asarray(bytearray(fv)).astype(np.float32)

        annoy_results = self.annoy_index.get_nns_by_vector(arr, k, search_k=5000, include_distances=True)

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
            list.append(SearchResult(item.priority, post))

        return list

    def close(self):
        self.listenthread.stop()
        self.p.close()
