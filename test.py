import cv2
import redis
from sqlalchemy import create_engine

from rep0st import rep0st

rep = rep0st(
    create_engine('mysql+cymysql://rep0st:rep0stpw@localhost/rep0st?charset=utf8'),
    redis.StrictRedis(host='localhost', port=6379, db=0),
    "/media/pr0gramm/images")

image = cv2.imread(str('test.jpg'), cv2.IMREAD_COLOR)

res = rep.get_index().search(image)
print(res)

rep.close()