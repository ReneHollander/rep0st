import logging
from pathlib import Path
from typing import BinaryIO, NewType, Optional

from absl import flags
from injector import Module, provider, ProviderOf, inject, singleton
import jinja2
from jinja2 import FileSystemLoader, Template, select_autoescape
import requests
from werkzeug import Request, Response
from werkzeug.routing import Rule

from rep0st.db.post import PostRepository, PostRepositoryModule
from rep0st.framework import Environment
from rep0st.framework.app import COMMIT_SHA
from rep0st.framework.data.transaction import transactional
from rep0st.framework.web import endpoint, request_data
from rep0st.framework.webpack import Webpack
from rep0st.service.media_service import ImageDecodeException, NoMediaFoundException
from rep0st.service.post_search_service import PostSearchService, PostSearchServiceModule
from rep0st.web import MediaHelper

log = logging.getLogger(__name__)

MainTemplate = NewType('MainTemplate', Template)

FLAGS = flags.FLAGS
flags.DEFINE_string(
    'google_analytics_measurement_id', None,
    'When set, adds a GA snippet to all pages reporting statistics to the given measurement ID.'
)


class MainModule(Module):

  def configure(self, binder):
    binder.install(PostSearchServiceModule)
    binder.install(PostRepositoryModule)
    binder.install(TemplateModule)
    binder.bind(Main)


class _TemplateEnvironment(jinja2.Environment):

  def __init__(self, env: Environment, webpack: Webpack):
    args = {}
    args.update(auto_reload=False)
    if env == Environment.DEVELOPMENT:
      args.update(cache_size=0, auto_reload=True)

    super(_TemplateEnvironment, self).__init__(
        loader=FileSystemLoader(Path(__file__).parent.absolute()),
        autoescape=select_autoescape(),
        **args)
    self.globals['WEBPACK'] = webpack
    self.globals['FRAMEWORK_BUILD_INFO'] = {'git_sha': COMMIT_SHA}
    if FLAGS.google_analytics_measurement_id:
      self.globals['GA'] = {
          'measurement_id': FLAGS.google_analytics_measurement_id
      }


class TemplateModule(Module):

  @provider
  @singleton
  def provide_environment(self, env: Environment,
                          webpack: Webpack) -> jinja2.Environment:
    return _TemplateEnvironment(env, webpack)

  @provider
  def provide_main_template(self,
                            environment: jinja2.Environment) -> MainTemplate:
    return environment.get_template('main.html.j2')


@singleton
class Main(MediaHelper):
  post_search_service: PostSearchService = None
  post_repository: PostRepository = None
  main_template: ProviderOf[MainTemplate] = None

  @inject
  def __init__(self, post_search_service: PostSearchService,
               post_repository: PostRepository,
               main_template: ProviderOf[MainTemplate]):
    self.post_search_service = post_search_service
    self.post_repository = post_repository
    self.main_template = main_template

  @transactional()
  def get_statistics(self):
    return {'latest_post': self.post_repository.get_latest_post_id()}

  def render(self, status=200, **kwargs):
    return Response(
        self.main_template.get().render(stats=self.get_statistics(), **kwargs),
        status=status,
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
      return self.render(status=400, error='Entweder Datei oder URL angeben!')

    if not file and not url:
      return self.render(status=400, error='Datei oder URL angeben!')

    data = None

    if file:
      data = file.read()

    if url:
      data = self._file_from_url(url)
      if not data:
        return self.render(
            status=400, error='Bild konnte nicht von der URL geladen werden!')

    try:
      results = self.post_search_service.search_file(data)
      return self.render(search_results=results)
    except (NoMediaFoundException, ImageDecodeException):
      return self.render(status=400, error='Ungültiges Bild!')
    except Exception:
      log.exception('Error occured when searching for image')
      return self.render(
          status=500,
          error=f'Unbekanner Fehler! Bitte inkludiere die folgende Identifikation wenn ein Bug Report erstellt wird: {request_data.id}'
      )
