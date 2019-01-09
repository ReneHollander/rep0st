import time
from datetime import datetime

from logbook import Logger
from requests import Session

import config
from rep0st.database import Post, PostType, Tag

config.load()
log = Logger('pr0gramm API')
s = Session()

pr0gramm_logindata = {
    'name': config.pr0gramm_config['username'],
    'password': config.pr0gramm_config['password'],
}
baseurl_api = config.pr0gramm_config['baseurl']['api']
baseurl_img = config.pr0gramm_config['baseurl']['img']


def perform_login():
    while True:
        log.info("performing pr0gramm login")
        response = s.post(baseurl_api + "/user/login", data=pr0gramm_logindata)
        if response.status_code != 200:
            log.error("error logging in. retrying in 10 seconds. status {}: {}", response.status_code, response.text)
            time.sleep(10)
            continue
        if not response.json()['success']:
            log.error("error logging in. wrong username/password.")
            raise Exception("error logging in. wrong username/password.")
        if response.json()['ban']:
            log.error("error logging in. account is banned.")
            raise Exception("error logging in. account is banned.")
        return


def perform_request(url):
    error_count = 0
    while True:
        response = s.get(url)
        if response.status_code == 403:
            perform_login()
            continue
        elif response.status_code != 200:
            log.warn("request finished with status {}: {}. retrying in 3 seconds", response.status_code, response.text)
            error_count = error_count + 1
            if error_count > 3:
                log.warn("request to url {} failed too often, bailing", url)
                raise Exception("request to url " + url + " failed too often")
            time.sleep(3)
            continue

        return response


def iterate_posts(start=0):
    at_start = False

    while not at_start:
        url = baseurl_api + "/items/get?flags=15&newer=%d" % start
        log.debug("requesting api page {}", url)
        data = perform_request(url).json()
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
        url = baseurl_api + "/tags/latest?id=%d" % start
        log.debug("requesting api page {}", url)
        data = perform_request(url).json()

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
    return perform_request(baseurl_img + "/" + post.image).content
