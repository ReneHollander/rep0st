from absl import flags
from injector import Module

from rep0st.framework.data.elasticsearch import ElasticsearchModule

FLAGS = flags.FLAGS
flags.DEFINE_multi_string(
    'rep0st_elasticsearch_uris', 'http://localhost:9200',
    'Elasticsearch URIs used by rep0st to index features.')


class Rep0stElasticsearchModule(Module):

  def configure(self, binder):
    binder.install(ElasticsearchModule(FLAGS.rep0st_elasticsearch_uris))
