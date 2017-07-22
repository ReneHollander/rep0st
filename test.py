import cv2

import config

rep = config.create_rep0st()

image = cv2.imread(str('test.jpg'), cv2.IMREAD_COLOR)

res = rep.get_index().search(image)
print(res)

# rep.close()
