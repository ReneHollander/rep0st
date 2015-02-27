from __future__ import division
from __future__ import unicode_literals

import math
import gevent
import gevent.pool
import gevent.monkey

import dataset
import requests
import itertools
import logbook
import pathlib
import numpy

from clint.textui import progress
from PIL import Image
from first import first


class Post(object):
    def __init__(self, id, created, user, flags, image):
        """
        :param int id: The id of the post
        :param int created: UTC timestamp of the creation time of the post in seconds
        :param user: Name of the user who posted this item
        :param image: Linked post image
        """
        self.id = id
        self.user = user
        self.image = image
        self.flags = flags
        self.created = created

    @property
    def animated(self):
        return self.image.endswith((".webm", ".gif"))

    @property
    def static(self):
        return self.image.endswith((".png", ".jpg"))

    @property
    def local_image(self):
        """Returns the local path of the posts image or video"""
        return pathlib.Path("env/data/images") / self.image

    def as_dict(self):
        """Converts this post into a dict. The dict can be read back using __init__"""
        return dict(id=self.id, user=self.user, image=self.image, flags=self.flags, created=self.created)


def chunks(iterable, size=100):
    """Yields chunks of the given size as tuples"""
    it = iter(iterable)
    chunk = tuple(itertools.islice(it, size))
    while chunk:
        yield chunk
        chunk = tuple(itertools.islice(it, size))


def iter_api_posts(start=None):
    """Iterates over all posts that the api provides,
    starting at the post witht he given id.
    """
    at_end = False

    while not at_end and start != 1:
        # build url for next page
        url = "http://pr0gramm.com/api/items/get?flags=7"
        if start is not None:
            url += "&older=%d" % start

        # perform api request
        #: :type: requests.Response
        logbook.debug("requesting api page {}", url)
        response = requests.get(url)
        response.raise_for_status()

        # parse response
        data = response.json()
        at_end = data["atEnd"]

        # create posts
        for item in data.get("items", ()):
            post = Post(item["id"], item["created"], item["user"], item["flags"], item["image"])
            start = post.id
            yield post


def download_posts(db, start=None, tablename="posts"):
    """Downloads all posts and adds them to the given datasets posts table.
    Download will stop if an already existing post is reached.

    :param dataset.Database db: The dataset to use
    """
    for chunk in chunks(iter_api_posts(start), 100):
        with db as tx:
            posts_table = tx[tablename]
            for post in chunk:
                if posts_table.find_one(id=post.id):
                    return

                posts_table.insert(post.as_dict())


def download_image(post):
    """Downloads the image of a post, if it was not yet downloaded.

    :param Post post: The post to downoad the image for
    """
    image_path = post.local_image
    if image_path.exists():
        return

    url = "http://img.pr0gramm.com/" + post.image

    #: :type: requests.Response
    response = requests.get(url)
    response.raise_for_status()

    # really download the image
    content = response.content
    with create_open(image_path) as fp:
        fp.write(content)


def create_open(path):
    """Ensures that the file at the given path does not exists
    and ensures that the parent directory is created
    """
    path = pathlib.Path(path)
    parent = path.parent
    if not parent.exists():
        parent.mkdir(parents=True)

    if path.exists():
        raise IOError("file already exists")

    return path.open("wb")


def db_posts(table):
    """Iterates over all posts in the database"""
    return (Post(**p) for p in table.find(order_by="-id", _step=None))


def download_images(posts):
    """Downloads images for the given posts"""
    pool = gevent.pool.Pool(size=96)
    for post in progress.bar(posts, width=60, every=100):
        if not post.static:
            continue

        pool.spawn(download_image, post)

    # wait for all jobs to finish
    pool.join()


def open_dataset():
    """Opens the database"""
    db = dataset.connect("sqlite:///env/data/post.db")
    db.query("PRAGMA busy_timeout=2500;")
    return db


def main():
    db = open_dataset()

    # download new posts
    download_posts(db)

    # get the oldest post and download even older posts
    posts_table = db["posts"]
    oldest_post = first(posts_table.find(order_by="id", _limit=1))
    if oldest_post and oldest_post["id"] != 1:
        download_posts(db, start=oldest_post["id"])

    # get a list of all the posts
    posts = list(db_posts(db["posts"]))

    # download images
    download_images(posts)


if __name__ == '__main__':
    gevent.monkey.patch_all()
    main()
