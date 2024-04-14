import logging
import time
from datetime import datetime, timezone
from typing import Iterator, NamedTuple, Optional

from absl import flags
from injector import Module, provider, singleton
from prometheus_client import Counter
from requests import RequestException, Response, Session, Timeout

from rep0st.db.post import Post, Status, post_type_from_media_path
from rep0st.db.tag import Tag
from rep0st.util import get_secret

log = logging.getLogger(__name__)
FLAGS = flags.FLAGS
flags.DEFINE_string('pr0gramm_api_user', None,
                    'Name of the pr0gramm user to use the API with.')
flags.DEFINE_string(
    'pr0gramm_api_user_file', None,
    'Path to the file containing the pr0gramm user to use the API with.')
flags.mark_flags_as_mutual_exclusive(
    ['pr0gramm_api_user', 'pr0gramm_api_user_file'], required=True)
flags.DEFINE_string('pr0gramm_api_password', None,
                    'Password of the pr0gramm user to use the API with.')
flags.DEFINE_string(
    'pr0gramm_api_password_file', None,
    'Path to the file containing the password of the pr0gramm user to use the API with.'
)
flags.mark_flags_as_mutual_exclusive(
    ['pr0gramm_api_password', 'pr0gramm_api_password_file'], required=True)
flags.DEFINE_string('pr0gramm_api_baseurl_api', 'https://pr0gramm.com/api',
                    'Baseurl for the pr0gramm API.')
flags.DEFINE_string('pr0gramm_api_baseurl_img', 'https://img.pr0gramm.com',
                    'Baseurl for the pr0gramm image API.')
flags.DEFINE_string('pr0gramm_api_baseurl_vid', 'https://vid.pr0gramm.com',
                    'Baseurl for the pr0gramm image API.')
flags.DEFINE_string('pr0gramm_api_baseurl_full', 'https://full.pr0gramm.com',
                    'Baseurl for the pr0gramm image API.')

flags.DEFINE_integer('pr0gramm_api_limit_id_to', None, (
    'If set, the API will indicate only posts below the limit id will be '
    'returned. Used to for debugging and building a small test environment locally'
))

logins_z = Counter('rep0st_pr0gramm_api_logins',
                   'Number of logins to pr0gramm by status.', ['status'])
logins_z.labels(status='ok')
logins_z.labels(status='banned')
logins_z.labels(status='wrong_credentials')
logins_z.labels(status='retried')
logins_z.labels(status='unknown')
requests_z = Counter('rep0st_pr0gramm_api_requests',
                     'Number of requests to the pr0gramm API by status.',
                     ['status'])
requests_z.labels(status='ok')
requests_z.labels(status='unknown')
requests_z.labels(status='not_found')


class LoginException(Exception):
  pass


class APIException(Exception):
  pass


class MediaPath(NamedTuple):
  base_url: str
  path: str


@singleton
class Pr0grammAPI:
  api_user: str = None
  api_password: str = None
  baseurl_api: str = None
  baseurl_img: str = None
  baseurl_vid: str = None
  baseurl_full: str = None
  limit_id_to: int = None
  session: Session = Session()

  def __init__(self,
               api_user: str,
               api_password: str,
               baseurl_api: str,
               baseurl_img: str,
               baseurl_vid: str,
               baseurl_full: str,
               limit_id_to: Optional[int] = None):
    self.api_user = api_user
    self.api_password = api_password
    self.baseurl_api = baseurl_api
    self.baseurl_img = baseurl_img
    self.baseurl_vid = baseurl_vid
    self.baseurl_full = baseurl_full
    self.limit_id_to = limit_id_to

  def perform_login(self) -> None:
    error_count = 0
    while True:
      log.debug(f'Performing pr0gramm login with user {self.api_user}')
      try:
        response = self.session.post(
            self.baseurl_api + "/user/login",
            data={
                'name': self.api_user,
                'password': self.api_password
            })
        if response.status_code != 200:
          logins_z.labels(status=f'http_{response.status_code}').inc()
          raise RequestException(
              f'Request responded with status {response.status_code}')
      except RequestException as e:
        error_count = error_count + 1
        if error_count > 3:
          logins_z.labels(status='unknown').inc()
          raise LoginException(
              f'Error logging in with user {self.api_user}') from e
        logins_z.labels(status='retried').inc()
        log.exception(
            f'Error logging in with user {self.api_user}, retrying in 10 seconds'
        )
        time.sleep(10)
        continue
      body = response.json()
      if not body['success']:
        logins_z.labels(status='wrong_credentials').inc()
        raise LoginException(
            f'Error logging in with user {self.api_user}. Wrong username/password.'
        )
      if body['ban']:
        logins_z.labels(status='banned').inc()
        raise LoginException(
            f'Error logging in with user {self.api_user}. Account is banned.')
      logins_z.labels(status='ok').inc()
      log.info(f'Login to pr0gramm successful with user {self.api_user}')
      return

  def perform_request(self, url: str) -> Response:
    log.debug(f'Performing request to {url}')
    error_count = 0
    while True:
      try:
        response = self.session.get(url, timeout=60)
        if response.status_code == 403:
          self.perform_login()
          continue
        if response.status_code == 404:
          requests_z.labels(status=f'not_found').inc()
          raise APIException(f'Request to url {url} failed with 404')
        # Raise an error if there is one and retry the request.
        response.raise_for_status()
        requests_z.labels(status=f'ok').inc()
        return response
      except (RequestException | Timeout) as e:
        log.exception(
            f'Error sending get request to {url}. Retrying in {3 ** error_count} seconds...'
        )
        error_count = error_count + 1
        if error_count > 3:
          requests_z.labels(status='unknown').inc()
          raise APIException(f'Request to url {url} failed too often') from e
        time.sleep(3**error_count)
        continue

  def iterate_posts(self, start: int = 0) -> Iterator[Post]:
    if self.limit_id_to and start >= self.limit_id_to:
      return

    at_start = False

    while not at_start:
      data = self.perform_request(
          f'{self.baseurl_api}/items/get?flags=31&promoted=0&newer={start}'
      ).json()
      at_start = data['atStart']

      for item in data.get('items', ()):
        if self.limit_id_to and item['id'] >= self.limit_id_to:
          return
        post = Post()
        post.id = item['id']
        post.created = datetime.fromtimestamp(
            item['created'], timezone.utc) if item['created'] else None
        post.image = item['image'] or None
        post.thumb = item['thumb'] or None
        post.fullsize = item['fullsize'] or None
        post.width = item['width'] or None
        post.height = item['height'] or None
        post.audio = item['audio'] or False
        post.source = item['source'] or None
        post.flags = item['flags'] or None
        post.user = item['user'] or None
        post.type = post_type_from_media_path(item['image'])
        post.status = Status.NO_MEDIA
        start = post.id
        yield post

  def iterate_tags(self, start: int = 0) -> Iterator[Tag]:
    while True:
      data = self.perform_request(
          f'{self.baseurl_api}/tags/latest?id={start}').json()

      if len(data['tags']) == 0:
        break

      for item in data.get('tags', ()):
        tag = Tag()
        tag.id = item['id']
        tag.up = item['up'] or None
        tag.down = item['down'] or None
        tag.confidence = item['confidence'] or None
        tag.post_id = item['itemId'] or None
        tag.tag = item['tag'] or None
        start = tag.id
        yield tag

  def download_image(self, image_path: str) -> bytes:
    log.debug(f'Downloading image "{image_path}"')
    return self.perform_request(f'{self.baseurl_img}/{image_path}').content

  def download_fullsize(self, fullsize_path: str) -> bytes:
    log.debug(f'Downloading fullsize "{fullsize_path}"')
    return self.perform_request(f'{self.baseurl_full}/{fullsize_path}').content

  def download_video(self, video_path: str) -> bytes:
    log.debug(f'Downloading video "{video_path}"')
    return self.perform_request(f'{self.baseurl_vid}/{video_path}').content


class Pr0grammAPIModule(Module):

  @singleton
  @provider
  def provide_pr0gramm_api(self) -> Pr0grammAPI:
    return Pr0grammAPI(
        get_secret(FLAGS.pr0gramm_api_user, FLAGS.pr0gramm_api_user_file),
        get_secret(FLAGS.pr0gramm_api_password,
                   FLAGS.pr0gramm_api_password_file),
        FLAGS.pr0gramm_api_baseurl_api, FLAGS.pr0gramm_api_baseurl_img,
        FLAGS.pr0gramm_api_baseurl_vid, FLAGS.pr0gramm_api_baseurl_full,
        FLAGS.pr0gramm_api_limit_id_to)
