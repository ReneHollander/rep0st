from datetime import datetime

import requests
from logbook import Logger

from database import Post, PostType, Tag

log = Logger('pr0gramm API')


def iterate_posts(start=0):
    at_start = False

    while not at_start:
        url = "http://pr0gramm.com/api/items/get?flags=15&newer=%d" % start

        log.debug("requesting api page {}", url)
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        at_start = data["atStart"]

        # create posts
        for item in data.get("items", ()):
            post = Post()
            post.id = item['id']
            post.created = datetime.fromtimestamp(item['created'])
            post.image = item['image']
            post.thumb = item['thumb']
            post.fullsize = item['fullsize']
            post.width = item['width']
            post.height = item['height']
            post.audio = item['audio']
            post.source = item['source']
            post.flags = item['flags']
            post.user = item['user']
            post.type = PostType.fromImage(item['image'])
            start = post.id
            yield post


def iterate_tags(start=0):
    while True:
        url = "http://pr0gramm.com/api/tags/latest?id=%d" % start

        log.debug("requesting api page {}", url)
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        if len(data['tags']) == 0:
            break

        for item in data.get("tags", ()):
            tag = Tag()
            tag.id = item['id']
            tag.up = item['up']
            tag.down = item['down']
            tag.confidence = item['confidence']
            tag.post_id = item['itemId']
            tag.tag = item['tag']
            start = tag.id
            yield tag


def download_image(post):
    log.debug("downloading image \"{}\" from post {}", post.image, post)
    response = requests.get("http://img.pr0gramm.com/" + post.image)
    response.raise_for_status()
    return response.content
