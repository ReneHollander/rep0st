import logging
from typing import Any, List

from absl import flags
from injector import Binder, Module, inject, singleton

from rep0st.db.post import Post, PostRepository, PostRepositoryModule
from rep0st.framework import app
from rep0st.framework.data.transaction import transactional
from rep0st.framework.execute import execute
from rep0st.pr0gramm.api import Pr0grammAPI, Pr0grammAPIModule
from rep0st.service.download_media_service import DownloadMediaService, DownloadMediaServiceModule

log = logging.getLogger(__name__)

FLAGS = flags.FLAGS
flags.DEFINE_integer(
    'rep0st_fix_media_files_and_links_job_startid', None,
    'Start iterating posts from the pr0gramm at the given post id.')


class FixMediaFilesAndLinksJobModule(Module):

  def configure(self, binder: Binder):
    binder.install(PostRepositoryModule)
    binder.install(Pr0grammAPIModule)
    binder.install(DownloadMediaServiceModule)
    binder.bind(FixMediaFilesAndLinksJob)


@singleton
class FixMediaFilesAndLinksJob:
  api: Pr0grammAPI = None

  @inject
  def __init__(self, api: Pr0grammAPI, post_repository: PostRepository,
               download_media_service: DownloadMediaService):
    self.api = api
    self.post_repository = post_repository
    self.download_media_service = download_media_service

  @transactional()
  def fix_post(self, new_post: Post):
    old_post = self.post_repository.get_by_id(new_post.id).one()
    post = self.download_media_service.rename_media(old_post, new_post)
    post.thumb = new_post.thumb
    self.post_repository.persist(post)

  @execute()
  def fix_posts_job(self):
    startid = 0
    if FLAGS.rep0st_fix_media_files_and_links_job_startid:
      startid = FLAGS.rep0st_fix_media_files_and_links_job_startid

    for post in self.api.iterate_posts(start=startid):
      try:
        log.info(f'Fixing post {post.id}')
        self.fix_post(post)
      except Exception:
        log.exception(f'Error handling post {post.id} for rename')


def modules() -> List[Any]:
  return [FixMediaFilesAndLinksJobModule]


if __name__ == "__main__":
  app.run(modules)
