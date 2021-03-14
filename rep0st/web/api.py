import json
import logging
from typing import Any

from injector import Module, inject, singleton
from werkzeug import Request, Response
from werkzeug.routing import Rule

from rep0st.db.post import PostRepository
from rep0st.framework.app import COMMIT_SHA
from rep0st.framework.data.transaction import transactional
from rep0st.framework.web import endpoint
from rep0st.service.media_service import ImageDecodeException, NoMediaFoundException
from rep0st.service.post_search_service import PostSearchService, PostSearchServiceModule
from rep0st.util import AutoJSONEncoder
from rep0st.web import MediaHelper

log = logging.getLogger(__name__)


class ApiModule(Module):

  def configure(self, binder):
    binder.install(PostSearchServiceModule)
    binder.bind(Api)


@singleton
class Api(MediaHelper):
  post_search_service: PostSearchService = None
  post_repository: PostRepository = None

  @inject
  def __init__(self, post_search_service: PostSearchService,
               post_repository: PostRepository):
    self.post_search_service = post_search_service
    self.post_repository = post_repository

  def render(self,
             resp: Any = None,
             error: str = None,
             status: int = 200) -> Response:
    if error is not None:
      resp = {'error': error}
    return Response(
        json.dumps(resp, default=AutoJSONEncoder),
        status=status,
        mimetype='application/json')

  @endpoint(Rule('/api', methods=['GET']))
  def index(self, _):
    return self.render(
        resp={
            'msg': 'welcome to the rep0st API',
            'latest_post': self.post_repository.get_latest_post_id(),
            'build': {
                'git_sha': COMMIT_SHA
            }
        },
        status=200)

  def _search(self, data: bytes) -> Response:
    try:
      results = self.post_search_service.search_file(data)
    except NoMediaFoundException or ImageDecodeException:
      return self.render(error='invalid image', status=400)
    except:
      log.exception('Error while searching')
      return self.render(
          error='internal error searching while searching', status=500)

    return self.render(resp=[{
        'similarity': sr.score,
        'post': sr.post
    } for sr in results])

  @transactional()
  @endpoint(Rule('/api/search', methods=['POST']))
  def search_upload(self, request: Request):
    try:
      file = self._file_from_post_request(request)
      data = file.read()
    except:
      return self.render(error='no image', status=400)

    return self._search(data)

  @transactional()
  @endpoint(Rule('/api/search', methods=['GET']))
  def search_url(self, request: Request):
    url = request.args.get('url')
    if not url:
      return self.render(error='url parameter missing', status=400)
    data = self.file_from_url(url)
    if not data:
      return self.render(error='could not load image from url', status=400)
    return self._search(data)
