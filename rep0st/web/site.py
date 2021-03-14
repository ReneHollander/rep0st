import logging
from typing import BinaryIO, Optional

import requests
from injector import Module, inject, singleton
from werkzeug import Request, Response
from werkzeug.routing import Rule

from rep0st.db.post import PostRepository, PostRepositoryModule
from rep0st.framework.data.transaction import transactional
from rep0st.framework.web import endpoint
from rep0st.service.post_search_service import PostSearchService, PostSearchServiceModule
from rep0st.web import MediaHelper
from rep0st.web.templates import IndexTemplate

log = logging.getLogger(__name__)


class SiteModule(Module):

  def configure(self, binder):
    binder.install(PostSearchServiceModule)
    binder.install(PostRepositoryModule)
    binder.bind(Site)


@singleton
class Site(MediaHelper):
  post_search_service: PostSearchService = None
  post_repository: PostRepository = None
  index_template: IndexTemplate = None

  @inject
  def __init__(self, post_search_service: PostSearchService,
               post_repository: PostRepository, index_template: IndexTemplate):
    self.post_search_service = post_search_service
    self.post_repository = post_repository
    self.index_template = index_template

  @transactional()
  def get_statistics(self):
    return {'latest_post': self.post_repository.get_latest_post_id()}

  def render(self, **kwargs):
    return Response(
        self.index_template.render(stats=self.get_statistics(), **kwargs),
        mimetype='text/html')

  def _file_from_url(self, url: str) -> Optional[bytes]:
    try:
      resp = requests.get(url)
      resp.raise_for_status()
      return resp.content
    except:
      log.exception('Error getting file from url')
      return None

  def _file_from_post_request(self, req: Request) -> Optional[BinaryIO]:
    if 'image' not in req.files:
      return None

    image_file = req.files['image']
    if image_file.filename == '':
      return None

    return image_file

  @endpoint(Rule('/', methods=['GET']))
  def index(self, _) -> Response:
    return self.render()

  @transactional()
  @endpoint(Rule('/', methods=['POST']))
  def search(self, request: Request) -> Response:
    file = self._file_from_post_request(request)
    url = request.form.get('url')

    if file and url:
      return self.render(error='Entweder Datei oder URL angeben!')

    if not file and not url:
      return self.render(error='Datei oder URL angeben!')

    data = None

    if file:
      data = file.read()

    if url:
      data = self._file_from_url(url)
      if not data:
        return self.render(
            error='Bild konnte nicht von der URL geladen werden!')

    results = self.post_search_service.search_file(data)

    return self.render(search_results=results)
