from time import time

import redis
from annoy import AnnoyIndex
from sqlalchemy import create_engine

from database import Feature, FeatureType
from rep0st import rep0st
from util import SimplePriorityQueue

r = rep0st(
    create_engine('mysql+cymysql://rep0st:rep0stpw@localhost/rep0st?charset=utf8'),
    redis.StrictRedis(host='localhost', port=6379, db=0),
    "/media/pr0gramm/images")

post_id = 1480441
k = 20

u = AnnoyIndex(108, metric='euclidean')
start = time()
u.load('index_1.ann')
diff = time() - start
print("Time to load index: %.5fs" % (diff))

nearest_brute = SimplePriorityQueue(k)

# start = time()
# for feature in r.database.session.query(Feature).filter(Feature.type == FeatureType.FEATURE_VECTOR).yield_per(1000):
#     dist = u.get_distance(post_id, feature.post_id)
#     nearest_brute.add(dist, feature.post_id)
# diff = time() - start
# print("Time to bruteforce: %.5fs" % (diff))

start = time()
nearest_annoy = u.get_nns_by_item(post_id, k, include_distances=True, search_k=5000)
diff = time() - start
print("Time to annoy: %.5fs" % (diff))

print("Bruteforce\tAnnoy")
for i in range(0, k):
    # b_p, b_v = nearest_brute[i]
    a_p = nearest_annoy[1][i]
    a_v = nearest_annoy[0][i]
    print(str(a_p) + " " + str(a_v))
