import logging

from injector import Binder, Module, inject, singleton
from prometheus_client import Counter
from prometheus_client.metrics import Gauge

from rep0st import util
from rep0st.db.post import Post, PostRepository, PostRepositoryModule, Status
from rep0st.framework.data.transaction import transactional
from rep0st.pr0gramm.api import Pr0grammAPI, Pr0grammAPIModule
from rep0st.service.download_media_service import DownloadMediaException, DownloadMediaService, DownloadMediaServiceModule

log = logging.getLogger(__name__)

post_service_posts_added_z = Counter('rep0st_post_service_posts_added',
                                     'Number of posts added to database')
post_service_latest_post_id_z = Gauge(
    'rep0st_post_service_latest_processed_post', 'ID of the latest post seen.')
post_service_latest_post_in_database_z = Gauge(
    'rep0st_post_service_latest_post_in_database',
    'ID of the latest post in the database.')


class PostServiceModule(Module):

  def configure(self, binder: Binder):
    binder.install(Pr0grammAPIModule)
    binder.install(DownloadMediaServiceModule)
    binder.install(PostRepositoryModule)
    binder.bind(PostService)


@singleton
class PostService:
  api: Pr0grammAPI = None
  download_media_service: DownloadMediaService = None
  post_repository: PostRepository = None

  @inject
  def __init__(self, api: Pr0grammAPI,
               download_media_service: DownloadMediaService,
               post_repository: PostRepository):
    self.api = api
    self.download_media_service = download_media_service
    self.post_repository = post_repository
    post_service_latest_post_in_database_z.set_function(
        self.post_repository.get_latest_post_id)

  @transactional()
  def _process_posts(self, posts) -> None:
    log.debug(f'Processing {len(posts)} posts')
    for post in posts:
      log.debug(f'Downloading media for post {post.id}')
      try:
        self.download_media_service.download_media(post)
        post.status = Status.NOT_INDEXED
      except DownloadMediaException:
        post.status = Status.NO_MEDIA_FOUND
        log.exception(f'Error downloading media for post {post.id}')
        continue
    log.debug(f'Saving {len(posts)} posts to database')
    self.post_repository.persist_all(posts)
    post_service_posts_added_z.inc(len(posts))
    post_service_latest_post_id_z.set(posts[-1].id)
    log.debug(f'Processed {len(posts)} posts')

  def update_posts(self):
    latest_post = self.post_repository.get_latest_post_id()
    counter = 0
    log.info(f'Starting post update. Latest post {latest_post}')
    for posts in util.batch(100, self.api.iterate_posts(start=latest_post)):
      self._process_posts(posts)
      counter += len(posts)

    log.info(
        f'Finished updating posts. {counter} posts were added to the database')

  @transactional()
  def _mark_deleted(self, ids):
    count = self.post_repository.get_by_ids(ids).update(
        {Post.deleted: True}, synchronize_session=False)
    if count > 0:
      log.info(f'Marked {count} posts as deleted')

  def update_all_posts(self):
    last_id = 0
    to_mark_deleted = []
    for post in self.api.iterate_posts():
      if post.id != last_id + 1:
        to_mark_deleted += list(range(last_id + 1, post.id))
        if len(to_mark_deleted) > 100:
          self._mark_deleted(to_mark_deleted)
          to_mark_deleted = []

      last_id = post.id
