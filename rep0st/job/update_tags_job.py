import logging
from typing import Any, List

from absl import flags
from injector import Module, inject, singleton

from rep0st.framework import app
from rep0st.framework.scheduler import Scheduler
from rep0st.service.tag_service import TagService, TagServiceModule

log = logging.getLogger(__name__)
FLAGS = flags.FLAGS
flags.DEFINE_string(
    'rep0st_update_tags_job_schedule', '*/1 * * * *',
    'Schedule in crontab format for running the tag update job.')


class UpdateTagsJobModule(Module):

  def configure(self, binder):
    binder.install(TagServiceModule)
    binder.bind(UpdateTagsJob)


@singleton
class UpdateTagsJob:
  tag_service: TagService

  @inject
  def __init__(self, tag_service: TagService, scheduler: Scheduler):
    self.tag_service = tag_service
    scheduler.schedule(FLAGS.rep0st_update_tags_job_schedule,
                       self.update_tags_job)

  def update_tags_job(self):
    self.tag_service.update_tags()


def modules() -> List[Any]:
  return [UpdateTagsJobModule]


if __name__ == "__main__":
  app.run(modules)
