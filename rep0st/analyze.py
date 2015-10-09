import traceback

from clint.textui import progress
import concurrent.futures
import cv2
import numpy
import numpy.linalg
import os

import rep0st.download

EMPTY_FEATURE = numpy.zeros((3 * 36,))


def build_feature_vector_for_image(image):
    """Builds the feature vector for one loaded image and returns it"""
    assert len(image.shape) == 3 and image.shape[2] == 3

    # scale down image and convert to hsv
    scaled = cv2.resize(image, (6, 6), interpolation=cv2.INTER_AREA)
    scaled = cv2.cvtColor(scaled, cv2.COLOR_BGR2HSV)

    # extract image channels
    hue = scaled[:, :, 0] / 2
    sat = scaled[:, :, 1]
    val = scaled[:, :, 2]

    # concat channels for feature vector
    return numpy.hstack((hue.flat, sat.flat, val.flat))


def build_feature_vector(post):
    """Builds a feature vector for the given post."""
    image = cv2.imread(str(post.local_image), cv2.IMREAD_COLOR)
    features = build_feature_vector_for_image(image)
    if features is None:
        return EMPTY_FEATURE

    return features


def write_feature_vector(target, post, feature):
    """Writes the feature vector to the target array.
    The feature vector is written in the post.id-th row of the target.
    """
    assert post.id < len(target)
    target[post.id, 1:] = feature
    target[post.id, 0] = 1


def has_feature_vector(target, post):
    """Checks if the feature vector for the given post is already calculated"""
    assert post.id < len(target)
    return target[post.id, 0] == 1


def mmap_feature_file():
    """Maps the features.np in memory. The file must already exist"""
    print os.getcwd()
    return numpy.memmap("env/data/features.np", mode="r+",
                        dtype=numpy.uint8, shape=(2000000, 1 + 3 * 36))

def close_feature_file(features):
    print "closing feature file"
    features._mmap.close();

# noinspection PyBroadException
def build_feature_vector_wrapper(target, post):
    try:
        if not has_feature_vector(target, post):
            # calculate and map
            feature = build_feature_vector(post)
            write_feature_vector(target, post, feature)

    except:
        traceback.print_exc()


def update_feature_vectors(posts):
    """Calculates missing feature vectors for the given posts"""
    target = mmap_feature_file()

    with concurrent.futures.ThreadPoolExecutor(16) as pool:
        processed = pool.map(lambda p: build_feature_vector_wrapper(target, p), posts)

        # consume the iterable and print progress
        processed = progress.bar(processed, every=16, width=60, expected_size=len(posts))
        for _ in processed:
            pass

    # closes and flushes the file
    target.flush()


def main():
    db = rep0st.download.open_dataset()
    posts = (p for p in rep0st.download.db_posts(db["posts"]) if p.static)
    # posts = itertools.islice(posts, 1000)
    update_feature_vectors(tuple(posts))


if __name__ == '__main__':
    main()
