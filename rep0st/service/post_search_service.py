import logging
from typing import Collection, NamedTuple

from injector import Binder, Module, inject, singleton

from rep0st.analyze.feature_vector_analyzer import TYPE_NAME as FEATURE_VECTOR_TYPE
from rep0st.db.post import Post, PostRepository, PostRepositoryModule
from rep0st.index.post import PostIndex, PostIndexModule
from rep0st.service.analyze_service import AnalyzeService, AnalyzeServiceModule
from rep0st.service.media_service import DecodeMediaService, DecodeMediaServiceModule

log = logging.getLogger(__name__)


class PostSearchServiceModule(Module):

  def configure(self, binder: Binder):
    binder.install(PostIndexModule)
    binder.install(AnalyzeServiceModule)
    binder.install(PostRepositoryModule)
    binder.install(DecodeMediaServiceModule)
    binder.bind(PostSearchService)


class SearchResult(NamedTuple):
  score: float
  post: Post


@singleton
class PostSearchService:
  post_index: PostIndex = None
  decode_media_service: DecodeMediaService = None
  analyze_service: AnalyzeService = None
  post_repository: PostRepository = None

  @inject
  def __init__(self, post_index: PostIndex,
               decode_media_service: DecodeMediaService,
               analyze_service: AnalyzeService,
               post_repository: PostRepository):
    self.post_index = post_index
    self.decode_media_service = decode_media_service
    self.analyze_service = analyze_service
    self.post_repository = post_repository

  def search_file(self, data: bytes) -> Collection[SearchResult]:
    image = list(self.decode_media_service.decode_image_from_buffer(data))[0]
    feature = [
        float(n / 255.0)
        for n in self.analyze_service.analyze(image)[FEATURE_VECTOR_TYPE]
    ]
    search_results = self.post_index.find_posts(feature)

    return [
        SearchResult(result.score,
                     self.post_repository.get_by_id(result.id).one())
        for result in search_results
    ]
