from typing import Iterable, NamedTuple

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Date, Document, InnerDoc, Integer, Keyword, Nested
from injector import Module, inject

from rep0st.analyze.feature_vector_analyzer import TYPE_NAME as FEATURE_VECTOR_TYPE
from rep0st.config.rep0st_elasticsearch import Rep0stElasticsearchModule
from rep0st.db.post import Post as DBPost
from rep0st.framework.data.elasticsearch import ElastiknnDenseFloatVectorL2LSHMapping, Index


class PostIndexModule(Module):

  def configure(self, binder):
    binder.install(Rep0stElasticsearchModule)
    binder.bind(PostIndex)


class Frame(InnerDoc):
  id = Integer()
  feature_vector = ElastiknnDenseFloatVectorL2LSHMapping(108, 180, 5, 3)


class Post(Document):
  created = Date()
  flags = Keyword()
  type = Keyword()
  tags = Keyword()

  frames = Nested(Frame)

  # TODO: Figure out how to disable dynamic mappings.
  # dynamic = False

  class Index:
    name = 'posts'
    settings = {
        'number_of_shards': 6,
        'elastiknn': True,
    }


class SearchResult(NamedTuple):
  score: float
  id: int


class PostIndex(Index[Post]):

  @inject
  def __init__(self, elasticsearch: Elasticsearch):
    super().__init__(Post, elasticsearch=elasticsearch)

  def _index_post_from_post(self, post: DBPost) -> Post:
    index_post = Post()
    index_post.meta.id = post.id
    index_post.created = post.created
    index_post.type = post.type.value
    index_post.flags = [flag.value for flag in post.get_flags()]
    index_post.tags = [tag.tag for tag in post.tags]
    index_post.frames = [
        Frame(
            id=feature.id,
            feature_vector=[float(n / 255.0)
                            for n in feature.data])
        for feature in post.features
        if feature.type == FEATURE_VECTOR_TYPE
    ]
    return index_post

  def add_posts(self, posts: Iterable[Post]):

    def _it():
      for post in posts:
        yield self._index_post_from_post(post)

    self.save_all(_it())

  def find_posts(self, feature_vector):
    response = self.search().update_from_dict({
        'size': 50,
        'fields': [],
        '_source': False,
        'min_score': 0.3,
        'query': {
            'nested': {
                'path': 'frames',
                'query': {
                    'elastiknn_nearest_neighbors': {
                        'field': 'frames.feature_vector',
                        'vec': {
                            'values': feature_vector,
                        },
                        'model': 'lsh',
                        'similarity': 'l2',
                        'candidates': 500,
                        'probes': 1,
                    },
                },
            },
        },
    }).execute()

    for post in response:
      yield SearchResult(post.meta.score, post.meta.id)
