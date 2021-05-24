import logging
from typing import Dict, List, Optional, Tuple

import numpy
from injector import Binder, Module, inject, singleton
from joblib import Parallel, delayed, parallel_backend
from prometheus_client import Counter
from prometheus_client.metrics import Gauge
from sqlalchemy import and_

from rep0st import util
from rep0st.db.feature import Feature, FeatureRepository, FeatureRepositoryModule
from rep0st.db.post import Post, PostRepository, PostRepositoryModule, Status, Type as PostType
from rep0st.framework.data.transaction import transactional
from rep0st.index.post import PostIndex, PostIndexModule
from rep0st.service.analyze_service import AnalyzeService, AnalyzeServiceModule
from rep0st.service.media_service import ImageDecodeException, NoMediaFoundException, ReadMediaService, ReadMediaServiceModule

log = logging.getLogger(__name__)

feature_service_features_added_z = Counter(
    'rep0st_feature_service_features_added',
    'Number of features added to the index')
feature_service_latest_processed_post_z = Gauge(
    'rep0st_feature_service_latest_processed_post',
    'ID of the latest post where the feaures where processed')


class FeatureServiceModule(Module):

  def configure(self, binder: Binder):
    binder.install(PostRepositoryModule)
    binder.install(FeatureRepositoryModule)
    binder.install(AnalyzeServiceModule)
    binder.install(ReadMediaServiceModule)
    binder.install(PostIndexModule)
    binder.bind(FeatureService)


class WorkImage:
  id: int
  features: Dict[str, numpy.ndarray]

  def __init__(self, id: int, features: Dict[str, numpy.ndarray]):
    self.id = id
    self.features = features


class WorkPost:
  post: Post = None  # Do not touch from other threads, only passed around for use in main thread again.
  id: int = None
  type: PostType = None
  status: Status = None
  image: str = None
  fullsize: str = None
  images: List[WorkImage] = []

  def __init__(self, post: Post):
    self.post = post
    self.id = post.id
    self.type = post.type
    self.status = post.status
    self.image = post.image
    self.fullsize = post.fullsize
    self.images = []


@singleton
class FeatureService:
  read_media_service: ReadMediaService = None
  post_repository: PostRepository = None
  feature_repository: FeatureRepository = None
  analyze_service: AnalyzeService = None
  post_index: PostIndex = None

  @inject
  def __init__(self, read_media_service: ReadMediaService,
               post_repository: PostRepository,
               feature_repository: FeatureRepository,
               analyze_service: AnalyzeService, post_index: PostIndex):
    self.read_media_service = read_media_service
    self.post_repository = post_repository
    self.feature_repository = feature_repository
    self.analyze_service = analyze_service
    self.post_index = post_index

  def _process_work_post(self, work_post: WorkPost) -> WorkPost:
    try:
      for i, image in enumerate(self.read_media_service.get_images(work_post)):
        work_post.images.append(
            WorkImage(i, self.analyze_service.analyze(image)))
      work_post.status = Status.INDEXED
    except NoMediaFoundException:
      work_post.status = Status.NO_MEDIA_FOUND
      log.exception(
          f'Error getting images for post {work_post.id}. No features are generated for it and post marked with NO_MEDIA_FOUND'
      )
    except ImageDecodeException:
      work_post.status = Status.MEDIA_BROKEN
      log.exception(
          f'Error getting images for post {work_post.id}. No features are generated for it and post marked with IMAGE_BROKEN'
      )
    return work_post

  def add_features_to_posts(self,
                            posts: List[Post],
                            parallel: Optional[Parallel] = None) -> None:
    work_posts = [WorkPost(post) for post in posts]

    if parallel:
      work_posts = parallel(
          delayed(self._process_work_post)(work_post)
          for work_post in work_posts)
    else:
      work_posts = [
          self._process_work_post(work_post) for work_post in work_posts
      ]

    for work_post in work_posts:
      work_post.post.status = work_post.status
      if work_post.post.status == Status.INDEXED:
        for image in work_post.images:
          for type, data in image.features.items():
            feature = Feature()
            feature.id = image.id
            feature.type = type
            feature.data = data
            work_post.post.features.append(feature)

  @transactional()
  def _process_features(
      self,
      post_type: PostType,
      parallel: Optional[Parallel] = None) -> Optional[Tuple[int, int]]:
    posts = self.post_repository.get_posts_missing_features(
        type=post_type).limit(250).all()
    if len(posts) == 0:
      return None
    log.debug(f'Calculating features for {len(posts)} posts')
    self.add_features_to_posts(posts, parallel=parallel)
    feature_count = sum([len(post.features) for post in posts])
    log.debug(
        f'Saving {feature_count} features for {len(posts)} posts to database')
    self.post_repository.persist_all(posts)
    # TODO(#34): Start adding video features to elasticsearch index
    if post_type == PostType.IMAGE:
      log.debug(
          f'Saving {feature_count} features for {len(posts)} posts to elasticsearch'
      )
      self.post_index.add_posts(posts)
    feature_service_latest_processed_post_z.set(
        max(posts, key=lambda p: p.id).id)
    feature_service_features_added_z.inc(feature_count)
    log.info(f'Processed {feature_count} features')
    return len(posts), feature_count

  def update_features(self, post_type: PostType):
    log.info(f'Starting feature update for post type {post_type}')
    post_counter = 0
    feature_counter = 0
    with parallel_backend('threading'), Parallel() as parallel:
      while True:
        result = self._process_features(post_type, parallel=parallel)
        if result is None:
          break
        post_counter += result[0]
        feature_counter += result[1]

    log.info(
        f'Finished updating features. {feature_counter} features for {post_counter} posts were added to the database'
    )

  def backfill_features(self):
    log.info('Starting feature backfill')
    it = self.post_repository.query().filter(
        and_(Post.status == Status.INDEXED, Post.type == PostType.IMAGE,
             Post.deleted == False))
    it = it.yield_per(1000)
    it = util.iterator_every(
        it, every=10000, msg='Backfilled {current} features')
    self.post_index.add_posts(it)
    log.info('Finished backfilling features')
