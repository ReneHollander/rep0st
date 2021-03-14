import logging
from typing import Any, List

from injector import Binder, Module, inject, singleton

from rep0st.db.post import PostRepository, PostRepositoryModule, post_status_type_deleted_index
from rep0st.framework import app
from rep0st.framework.execute import execute
from rep0st.index.post import PostIndex, PostIndexModule
from rep0st.service.analyze_service import AnalyzeService, AnalyzeServiceModule
from rep0st.service.feature_service import FeatureService, FeatureServiceModule
from rep0st.service.post_search_service import PostSearchService, PostSearchServiceModule
from rep0st.service.post_service import PostService, PostServiceModule

log = logging.getLogger(__name__)


class TestModule(Module):

  def configure(self, binder: Binder):
    binder.install(PostRepositoryModule)
    binder.install(PostServiceModule)
    binder.install(PostIndexModule)
    binder.install(PostSearchServiceModule)
    binder.install(AnalyzeServiceModule)
    binder.install(FeatureServiceModule)
    binder.bind(Test)


@singleton
class Test:
  post_service: PostService
  post_search_service: PostSearchService
  post_index: PostIndex
  post_repository: PostRepository
  analyze_service: AnalyzeService
  feature_service: FeatureService

  @inject
  def __init__(self, post_service: PostService,
               post_search_service: PostSearchService, post_index: PostIndex,
               post_repository: PostRepository, analyze_service: AnalyzeService,
               feature_service: FeatureService):
    self.post_service = post_service
    self.post_search_service = post_search_service
    self.post_index = post_index
    self.post_repository = post_repository
    self.analyze_service = analyze_service
    self.feature_service = feature_service

  @execute()
  def test_main(self):
    pass
    # self.post_service.update_all_posts()
    # post_status_type_deleted_index.create()
    # print(self.post_repository.get_posts_missing_features(type=PostType.IMAGE))
    # self.post_index.init()  # self.post_index.
    # self.feature_service.backfill_features()


def modules() -> List[Any]:
  return [TestModule]


if __name__ == "__main__":
  app.run(modules)
