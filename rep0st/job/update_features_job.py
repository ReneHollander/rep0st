import logging
from typing import Any, List

from absl import flags
from injector import Binder, Module, inject, singleton

from rep0st.db import PostType
from rep0st.framework import app
from rep0st.framework.scheduler import Scheduler, SchedulerModule
from rep0st.service.feature_service import FeatureService, FeatureServiceModule

log = logging.getLogger(__name__)
FLAGS = flags.FLAGS
flags.DEFINE_string(
    'rep0st_update_features_job_schedule', '* * * * * *',
    'Schedule in crontab format for running the feature update job.')
flags.DEFINE_enum_class(
    'rep0st_update_features_post_type', PostType.IMAGE, PostType,
    'The post type (image, video, ...) this job should index.')


class UpdateFeaturesJobModule(Module):

  def configure(self, binder: Binder):
    binder.install(FeatureServiceModule)
    binder.install(SchedulerModule)
    binder.bind(UpdateFeaturesJob)


@singleton
class UpdateFeaturesJob:
  feature_service: FeatureService

  @inject
  def __init__(self, feature_service: FeatureService, scheduler: Scheduler):
    self.feature_service = feature_service
    scheduler.schedule(FLAGS.rep0st_update_features_job_schedule,
                       self.update_feature_job)

  def update_feature_job(self):
    self.feature_service.update_features(FLAGS.rep0st_update_features_post_type)


def modules() -> List[Any]:
  return [UpdateFeaturesJobModule]


if __name__ == "__main__":
  app.run(modules)
