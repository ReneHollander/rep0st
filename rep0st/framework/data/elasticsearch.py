import logging
from typing import Generic, Iterable, List, Type, TypeVar

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch_dsl import Float, Search
from elasticsearch_dsl.query import Query
from injector import Module, provider, singleton

elasticsearch_logger = logging.getLogger('elasticsearch')
elasticsearch_logger.setLevel(logging.INFO)

K = TypeVar('K')


class ElasticsearchModule(Module):
  hosts: List[str]

  def __init__(self, hosts: List[str]):
    self.hosts = hosts

  @provider
  @singleton
  def provide_elasticsearch(self) -> Elasticsearch:
    return Elasticsearch(
        self.hosts,
        sniff_on_start=True,
        sniff_on_connection_fail=True,
        sniffer_timeout=60)


class ElastiknnDenseFloatVectorL2LSHMapping(Float):
  name = "elastiknn_dense_float_vector"

  def __init__(self, dims, hash_tables, hash_functions, bucket_width):
    super(Float, self).__init__(
        elastiknn={
            'dims': dims,
            'model': 'lsh',
            'similarity': 'l2',
            'L': hash_tables,
            'k': hash_functions,
            'w': bucket_width,
        })


class Wrapper(Query):
  name = "elastiknn_nearest_neighbors"


class Index(Generic[K]):
  elasticsearch: Elasticsearch = None

  def __init__(self, k_type: Type[K], elasticsearch: Elasticsearch):
    self._k_type = k_type
    self.elasticsearch = elasticsearch
    if not self._k_type._index.exists(using=self.elasticsearch):
      self._k_type.init(using=self.elasticsearch)

  def save(self, value: K):
    return value.save(using=self.elasticsearch)

  def save_all(self, values: Iterable[K]):

    def _it():
      for value in values:
        yield value.to_dict(include_meta=True)

    return bulk(self.elasticsearch, _it())

  def search(self) -> Search:
    return self._k_type.search(using=self.elasticsearch)

  def delete(self, value: K):
    return value.delete(using=self.elasticsearch)
