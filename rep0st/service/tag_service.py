import logging

from injector import Module, inject, singleton

from rep0st import util
from rep0st.db.tag import TagRepository, TagRepositoryModule
from rep0st.pr0gramm.api import Pr0grammAPI

log = logging.getLogger(__name__)


class TagServiceModule(Module):

  def configure(self, binder):
    binder.install(TagRepositoryModule)
    binder.bind(TagService)


@singleton
class TagService:
  api: Pr0grammAPI = None
  tag_repository: TagRepository = None

  @inject
  def __init__(self, api: Pr0grammAPI, tag_repository: TagRepository):
    self.api = api
    self.tag_repository = tag_repository

  def update_tags(self):
    latest_tag = self.tag_repository.get_latest_tag_id()
    log.info(f'Starting tag updated. Latest tag {latest_tag}')
    counter = 0
    for batch in util.batch(10000, self.api.iterate_tags(start=latest_tag)):
      counter += len(batch)
      log.info(f'Saving {len(batch)} tags')
      self.tag_repository.persist_bulk(batch)
    log.info(
        f'Finished updating tags. {counter} tags were added to the database')
