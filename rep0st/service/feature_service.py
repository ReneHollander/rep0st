import logging
from multiprocessing import TimeoutError
from typing import List, Optional, Tuple

import numpy
from numpy.typing import NDArray
from injector import Binder, Module, inject, singleton
from joblib import Parallel, delayed, parallel_backend
from prometheus_client import Counter
from prometheus_client.metrics import Gauge

from rep0st.db import PostType
from rep0st.db.feature import FeatureVector, FeatureVectorRepository, FeatureVectorRepositoryModule
from rep0st.db.post import Post, PostErrorStatus, PostRepository, PostRepositoryModule
from rep0st.framework.data.transaction import transactional
from rep0st.service.analyze_service import AnalyzeService, AnalyzeServiceModule
from rep0st.service.media_service import ImageDecodeException, NoMediaFoundException, ReadMediaService, ReadMediaServiceModule

log = logging.getLogger(__name__)

feature_service_features_added_z = Counter(
    'rep0st_feature_service_features_added',
    'Number of features added to the index.')
feature_service_latest_processed_post_z = Gauge(
    'rep0st_feature_service_latest_processed_post',
    'ID of the latest post where the features where processed.')
feature_service_latest_post_with_features_in_database_z = Gauge(
    'rep0st_feature_service_latest_post_with_features_in_database',
    'ID of the latest post in the database.')
feature_service_post_count_with_features_in_database_z = Gauge(
    'rep0st_feature_service_post_count_with_features_in_database',
    'Number of posts with features in the database.')


class FeatureServiceModule(Module):

  def configure(self, binder: Binder):
    binder.install(PostRepositoryModule)
    binder.install(FeatureVectorRepositoryModule)
    binder.install(AnalyzeServiceModule)
    binder.install(ReadMediaServiceModule)
    binder.bind(FeatureService)


class WorkImage:
  id: int
  feature_vector: NDArray[numpy.float32]

  def __init__(self, id: int, feature_vector: NDArray[numpy.float32]):
    self.id = id
    self.feature_vector = feature_vector


class WorkPost:
  post: Post = None  # Do not touch from other threads, only passed around for use in main thread again.
  id: int = None
  type: PostType = None
  error_status: PostErrorStatus = None
  image: str = None
  fullsize: str = None
  images: List[WorkImage] = []
  started: bool = False
  done: bool = False

  def __init__(self, post: Post):
    self.post = post
    self.id = post.id
    self.type = post.type
    self.error_status = post.error_status
    self.image = post.image
    self.fullsize = post.fullsize
    self.images = []
    self.started = False
    self.done = False


@singleton
class FeatureService:
  read_media_service: ReadMediaService = None
  post_repository: PostRepository = None
  feature_vector_repository: FeatureVectorRepository = None
  analyze_service: AnalyzeService = None

  @inject
  def __init__(self, read_media_service: ReadMediaService,
               post_repository: PostRepository,
               feature_vector_repository: FeatureVectorRepository,
               analyze_service: AnalyzeService):
    self.read_media_service = read_media_service
    self.post_repository = post_repository
    self.feature_vector_repository = feature_vector_repository
    self.analyze_service = analyze_service
    feature_service_latest_post_with_features_in_database_z.set_function(
        self.post_repository.get_latest_post_id_with_features)
    feature_service_post_count_with_features_in_database_z.set_function(
        self.post_repository.post_count_with_features)

  def _process_work_post(self, work_post: WorkPost) -> WorkPost:
    work_post.started = True
    try:
      for i, image in enumerate(self.read_media_service.get_images(work_post)):
        work_post.images.append(
            WorkImage(i, self.analyze_service.analyze(image)))
      work_post.error_status = None
    except NoMediaFoundException:
      work_post.error_status = PostErrorStatus.NO_MEDIA_FOUND
      log.exception(
          f'Error getting images for post {work_post.id}. No features are generated for it and post marked with NO_MEDIA_FOUND'
      )
    except ImageDecodeException:
      work_post.error_status = PostErrorStatus.MEDIA_BROKEN
      log.exception(
          f'Error getting images for post {work_post.id}. No features are generated for it and post marked with IMAGE_BROKEN'
      )
    work_post.done = True

  def add_features_to_posts(
      self,
      posts: List[Post],
      parallel: Optional[Parallel] = None) -> List[FeatureVector]:
    work_posts = [WorkPost(post) for post in posts]

    if parallel:
      try:
        parallel(
            delayed(self._process_work_post)(work_post)
            for work_post in work_posts)
      except TimeoutError:
        pass
    else:
      for work_post in work_posts:
        self._process_work_post(work_post)

    log.debug(f'Calculated features for {len(posts)} posts')

    feature_vectors = []
    for work_post in work_posts:
      work_post.post.error_status = work_post.error_status
      if work_post.started and not work_post.done:
        log.warn(
            f'Post {work_post.post} could not be processed within 120s. Marking MEDIA_BROKEN'
        )
        work_post.post.error_status = PostErrorStatus.MEDIA_BROKEN
      if work_post.post.error_status == None:
        for image in work_post.images:
          work_post.post.features_indexed = True
          feature_vectors.append(
              FeatureVector(
                  post=work_post.post,
                  id=image.id,
                  post_type=work_post.type,
                  vec=image.feature_vector))
    return feature_vectors

  @transactional(autoflush=False)
  def _process_features(
      self,
      post_type: PostType,
      parallel: Optional[Parallel] = None) -> Tuple[int, int, int]:
    posts = self.post_repository.get_posts_missing_features(
        type=post_type).limit(1000).all()
    if len(posts) == 0:
      return 0, 0, 0
    log.debug(f'Calculating features for {len(posts)} posts')
    feature_vectors = self.add_features_to_posts(posts, parallel=parallel)
    feature_count = len(feature_vectors)
    log.debug(
        f'Saving {feature_count} features for {len(posts)} posts to database')
    self.feature_vector_repository.add_all(feature_vectors)
    self.post_repository.add_all(posts)
    max_post_id = max(posts, key=lambda p: p.id).id
    return len(posts), feature_count, max_post_id

  def update_features(self, post_type: PostType):
    log.info(f'Starting feature update for post type {post_type}')
    post_counter = 0
    feature_counter = 0
    with parallel_backend('threading'), Parallel(timeout=120.0) as parallel:
      while True:
        post_count, feature_count, max_post_id = self._process_features(
            post_type, parallel=parallel)
        if post_count == 0:
          break
        feature_service_latest_processed_post_z.set(max_post_id)
        feature_service_features_added_z.inc(feature_count)
        log.info(
            f'Processed {feature_count} features for {post_count} posts. Latest post: {max_post_id}'
        )
        post_counter += post_count
        feature_counter += feature_count

    log.info(
        f'Finished updating features. {feature_counter} features for {post_counter} posts were added to the database'
    )
