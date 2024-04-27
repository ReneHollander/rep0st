import logging
from typing import Any, List

from absl import flags
from injector import Binder, Module, inject, singleton

from rep0st.framework import app
from rep0st.framework.scheduler import Scheduler, SchedulerModule
from rep0st.service.post_service import PostService, PostServiceModule

log = logging.getLogger(__name__)
FLAGS = flags.FLAGS
flags.DEFINE_string(
    'rep0st_update_posts_job_schedule', '* * * * * *',
    'Schedule in crontab format for running the post update job.')
flags.DEFINE_string(
    'rep0st_update_all_posts_job_schedule', '',
    'Schedule in crontab format for running the all post update job.')
flags.DEFINE_integer('rep0st_update_posts_end_id', None,
                     'Post ID at which to end the update posts job.')
flags.DEFINE_integer('rep0st_update_all_posts_start_id', None,
                     'Post ID at which to start the update all posts job.')
flags.DEFINE_integer('rep0st_update_all_posts_end_id', None,
                     'Post ID at which to end the update all posts job.')


class UpdatePostsJobModule(Module):

  def configure(self, binder: Binder):
    binder.install(PostServiceModule)
    binder.install(SchedulerModule)
    binder.bind(UpdatePostsJob)


@singleton
class UpdatePostsJob:
  post_service: PostService

  @inject
  def __init__(self, post_service: PostService, scheduler: Scheduler):
    self.post_service = post_service
    scheduler.schedule(FLAGS.rep0st_update_posts_job_schedule,
                       self.update_posts_job)
    scheduler.schedule(FLAGS.rep0st_update_all_posts_job_schedule,
                       self.update_all_posts_job)

  def update_posts_job(self):
    self.post_service.update_posts(end_id=FLAGS.rep0st_update_posts_end_id)

  def update_all_posts_job(self):
    self.post_service.update_all_posts(
        start_id=FLAGS.rep0st_update_all_posts_start_id,
        end_id=FLAGS.rep0st_update_all_posts_end_id)


def modules() -> List[Any]:
  return [UpdatePostsJobModule]


if __name__ == "__main__":
  app.run(modules)
