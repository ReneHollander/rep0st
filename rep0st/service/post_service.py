import logging

from injector import Binder, Module, inject, singleton
from prometheus_client import Counter
from prometheus_client.metrics import Gauge
from sqlalchemy import and_

from rep0st import util
from rep0st.db.post import Post, PostErrorStatus, PostRepository, PostRepositoryModule
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

  def _download_media(self, post: Post):
    log.debug(f'Downloading media for post {post.id}')
    try:
      self.download_media_service.download_media(post)
      post.error_status = None
    except DownloadMediaException:
      post.error_status = PostErrorStatus.NO_MEDIA_FOUND
      log.exception(f'Error downloading media for post {post.id}')

  @transactional(autoflush=False)
  def _process_posts(self, posts) -> None:
    log.debug(f'Processing {len(posts)} posts')
    for post in posts:
      self._download_media(post)
    log.debug(f'Saving {len(posts)} posts to database')
    self.post_repository.persist_all(posts)
    post_service_posts_added_z.inc(len(posts))
    post_service_latest_post_id_z.set(posts[-1].id)
    log.debug(f'Processed {len(posts)} posts')

  def update_posts(self, end_id: int | None = None):
    latest_post = self.post_repository.get_latest_post_id()
    counter = 0
    log.info(f'Starting post update. Latest post {latest_post}')
    for posts in util.batch(
        100, self.api.iterate_posts(start=latest_post + 1, end=end_id)):
      self._process_posts(posts)
      counter += len(posts)

    log.info(
        f'Finished updating posts. {counter} posts were added to the database')

  @transactional(autoflush=False)
  def _process_batch(self, batch_start_id: int, batch_end_id: int):
    log.info(f'Processing posts {batch_start_id}-{batch_end_id}')
    posts_from_api = {
        p.id: p
        for p in self.api.iterate_posts(start=batch_start_id, end=batch_end_id)
    }
    posts_from_db = {
        p.id: p for p in self.post_repository.get_posts().filter(
            and_(Post.id >= batch_start_id, Post.id <= batch_end_id))
    }
    to_save = []
    for i in range(batch_start_id, batch_end_id + 1):
      post_from_db = posts_from_db.get(i, None)
      post_from_api = posts_from_api.get(i, None)
      if post_from_api and not post_from_db:
        # Post returned by API, but is not in DB.
        log.debug(f'Adding missing post: {post_from_api}')
        self._download_media(post_from_api)
        to_save.append(post_from_api)
        continue
      if not post_from_db:
        # We never saw this post and it doesn't exist. Nothing we can do to bring it back :(
        log.debug(f'Ignoring post with id {i} since we never saw it')
        continue
      if not post_from_api:
        # Post not returned by API, but it is in DB.
        # Mark as deleted.
        if not post_from_db.deleted:
          log.debug(
              f'Marking post deleted since it is no longer in the API: {post_from_db}'
          )
          post_from_db.feature_vectors = []
          post_from_db.deleted = True
          # Remove the features from the DB for good measure.
          post_from_db.features = []
          post_from_db.features_indexed = False
          to_save.append(post_from_db)
        continue
      # Post is in both DB and API. Potentially update it.
      if post_from_db.deleted:
        log.debug(
            f'Unmarking post as deleted since the API contains it: {post_from_db}'
        )
        post_from_db.deleted = False
      if post_from_db.flags != post_from_api.flags:
        log.debug(
            f'Updating flags of post since they changed: {post_from_db}. post_from_db.flags={post_from_db.flags}, post_from_api.flags={post_from_api.flags}'
        )
        post_from_db.flags = post_from_api.flags
      old_error_status = post_from_db.error_status
      # Download media if not exists or broken.
      self._download_media(post_from_db)
      if old_error_status != post_from_db.error_status:
        # Remove the features. The update feature job will try to index the media again on the next run.
        post_from_db.features = []
        post_from_db.features_indexed = False
      to_save.append(post_from_db)
    self.post_repository.persist_all(to_save)

  def update_all_posts(self,
                       start_id: int | None = 1,
                       end_id: int | None = None):
    if not start_id:
      start_id = 1
    max_post_id_from_api = self.api.get_latest_post_id()
    if not max_post_id_from_api:
      log.error('Latest post id could not determined from pr0gramm API')
      return
    max_post_id_from_db = self.post_repository.get_latest_post_id()
    if end_id:
      end_id = min(max(max_post_id_from_api, max_post_id_from_db), end_id)
    else:
      end_id = max(max_post_id_from_api, max_post_id_from_db)
    for batch_start_id, batch_end_id in util.batched_ranges(
        start_id, end_id, 1000):
      self._process_batch(batch_start_id, batch_end_id)
