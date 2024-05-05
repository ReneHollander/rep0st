import logging
from typing import Collection, NamedTuple

from injector import Binder, Module, inject, singleton

from rep0st.db import PostType
from rep0st.db.post import Flag, Post, PostRepository, PostRepositoryModule
from rep0st.service.analyze_service import AnalyzeService, AnalyzeServiceModule
from rep0st.service.media_service import DecodeMediaService, DecodeMediaServiceModule

log = logging.getLogger(__name__)


class PostSearchServiceModule(Module):

  def configure(self, binder: Binder):
    binder.install(AnalyzeServiceModule)
    binder.install(PostRepositoryModule)
    binder.install(DecodeMediaServiceModule)
    binder.bind(PostSearchService)


class SearchResult(NamedTuple):
  score: float
  post: Post


@singleton
class PostSearchService:
  decode_media_service: DecodeMediaService = None
  analyze_service: AnalyzeService = None
  post_repository: PostRepository = None

  @inject
  def __init__(self, decode_media_service: DecodeMediaService,
               analyze_service: AnalyzeService,
               post_repository: PostRepository):
    self.decode_media_service = decode_media_service
    self.analyze_service = analyze_service
    self.post_repository = post_repository

  def search_file(self,
                  data: bytes,
                  flags: list[Flag] | None = None,
                  exact: bool | None = False) -> Collection[SearchResult]:
    image = list(self.decode_media_service.decode_image_from_buffer(data))[0]
    feature_vector = self.analyze_service.analyze(image)

    search_results = [
        SearchResult(score, post)
        for score, post in self.post_repository.search_posts(
            PostType.IMAGE,
            feature_vector,
            flags=flags,
            # Find a lot of candidates to ensure the filter by flag doesn't
            # yield empty results in case of a restrictive search.
            ef_search=1000,
            exact=exact).limit(50)
    ]

    return sorted(search_results, key=lambda sr: sr.score, reverse=True)
