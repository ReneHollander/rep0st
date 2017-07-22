import cv2

import config

rep = config.get_rep0st()

image = cv2.imread(str('test.jpg'), cv2.IMREAD_COLOR)

print(rep.get_statistics())

post = rep.database.get_post_by_id(2046642)
print(post)
print(post.get_flags())

exit(0)

res = rep.get_index().search(image)
print(res)
print(rep.get_statistics())

# rep.close()
