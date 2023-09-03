import logging
from typing import Any, List

from absl import flags
from injector import Binder, Module, inject, singleton

from rep0st.framework import app
from rep0st.framework.execute import execute
from rep0st.service.feature_service import FeatureService, FeatureServiceModule
from rep0st.db.post import Type as PostType

log = logging.getLogger(__name__)
FLAGS = flags.FLAGS
flags.DEFINE_enum_class(
    'rep0st_backfill_features_post_type', PostType.IMAGE, PostType,
    'The post type (image, video, ...) this job should index.')


class BackfillFeaturesJobModule(Module):

  def configure(self, binder: Binder):
    binder.install(FeatureServiceModule)
    binder.bind(BackfillFeaturesJob)


@singleton
class BackfillFeaturesJob:
  feature_service: FeatureService

  @inject
  def __init__(self, feature_service: FeatureService):
    self.feature_service = feature_service

  @execute()
  def backfill_feature_job(self):
    self.feature_service.backfill_features(
        FLAGS.rep0st_backfill_features_post_type)


def modules() -> List[Any]:
  return [BackfillFeaturesJobModule]


if __name__ == "__main__":
  app.run(modules)
