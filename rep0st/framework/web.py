import logging
import random
import threading
import time
from abc import ABC
from threading import Thread
from typing import Any, Callable, Collection, List, NamedTuple, NewType, Union

from absl import flags
from cheroot.wsgi import Server as WSGIServer
from injector import Binder, Injector, Module, inject, multiprovider, singleton
from prometheus_client.metrics import Counter, Gauge
from werkzeug import Request
from werkzeug.exceptions import HTTPException, InternalServerError
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.routing import Map, Rule
from wsgiref.types import WSGIApplication, WSGIEnvironment, StartResponse

from rep0st.framework.decorator import DecoratorProcessor
from rep0st.framework.execute import execute
from rep0st.framework.signal_handler import on_shutdown

FLAGS = flags.FLAGS
flags.DEFINE_string('webserver_bind_hostname', '',
                    'Hostname to which to bind the HTTP server to.')
flags.DEFINE_integer('webserver_bind_port', None,
                     'Port to which to bind the HTTP server to.')

_WebserverBindHostnameKey = NewType('_WebserverBindHostnameKey', str)
_WebserverBindPortKey = NewType('_WebserverBindPortKey', str)

log = logging.getLogger(__name__)
request_logger = logging.getLogger(__name__ + '.request')

framework_webserver_requests_z = Counter(
    'framework_webserver_requests',
    'Number of requests handled by the web server with the given status',
    ['status'])
framework_webserver_requests_z.labels(status=200)
framework_webserver_requests_z.labels(status=404)
framework_webserver_requests_z.labels(status=500)
framework_webserver_endpoint_requests_z = Counter(
    'framework_webserver_endpoint_requests',
    'Number of requests per rule and status', ['rule', 'method', 'status'])


def _get_status_code(status: str):
  if not status:
    return -1
  parts = status.split(' ')
  if len(parts) < 1:
    return -1
  status = parts[0]
  try:
    status = int(status)
  except ValueError:
    return -1
  return status


class RequestLocal(threading.local):
  id: str = None

  def __init__(self):
    pass

  def start(self):
    self.id = '%012x' % random.randrange(16**12)


request_data = RequestLocal()


class WSGILogger(WSGIApplication):
  app: WSGIApplication = None

  def __init__(self, app: WSGIApplication):
    self.app = app

  def __call__(self, environ: WSGIEnvironment, start_response: StartResponse):
    request_data.start()
    start = time.time()
    status = ""
    content_length = 0
    remote = f"{environ['REMOTE_ADDR']}:{environ['REMOTE_PORT']}"
    if 'HTTP_X_FORWARDED_FOR' in environ:
      remote = f"{environ['HTTP_X_FORWARDED_FOR']} (through {remote})"
    request_logger.info(
        f"{remote} - {environ['REQUEST_METHOD']} {environ['PATH_INFO']} {environ['SERVER_PROTOCOL']}"
    )

    def custom_start_response(status_, response_headers_, exc_info_=None):
      nonlocal status
      nonlocal content_length
      status = status_
      framework_webserver_requests_z.labels(
          status=_get_status_code(status)).inc()
      for name, value in response_headers_:
        if name.lower() == 'content-length':
          content_length = value
          break
      return start_response(status_, response_headers_, exc_info_)

    retval = self.app(environ, custom_start_response)
    runtime = (time.time() - start)
    request_logger.info(
        f"Finished with status {status}, took {runtime * 1000:.2f}ms, {content_length} bytes"
    )
    return retval


class MountPoint(NamedTuple):
  mount_path: str
  app: WSGIApplication


class WebApp(ABC):

  def get_mounts(self) -> List[MountPoint]:
    return []

  def get_rules(self) -> List[Rule]:
    return []


@singleton
class WebServer:
  bind_hostname: str = None
  bind_port: str = None
  wsgi_applications: List[WebApp] = None
  server: WSGIServer = None

  @inject
  def __init__(self, bind_hostname: _WebserverBindHostnameKey,
               bind_port: _WebserverBindPortKey,
               wsgi_applications: List[WebApp]):
    self.bind_hostname = bind_hostname
    self.bind_port = bind_port
    self.wsgi_applications = wsgi_applications

    self.url_map = Map(
        [rule for app in self.wsgi_applications for rule in app.get_rules()])
    self.mount_map = {
        mount.mount_path: mount.app for app in self.wsgi_applications
        for mount in app.get_mounts()
    }

  def _handler(self, environ: WSGIEnvironment, start_response: StartResponse):
    adapter = self.url_map.bind_to_environ(environ)
    try:
      rule, values = adapter.match(return_rule=True)
    except HTTPException as e:
      return e.get_response(environ)(environ, start_response)

    def custom_start_response(status_,
                              response_headers_,
                              exc_info_=None) -> StartResponse:
      framework_webserver_endpoint_requests_z.labels(
          rule=rule.rule,
          method=environ['REQUEST_METHOD'],
          status=_get_status_code(status_)).inc()
      return start_response(status_, response_headers_, exc_info_)

    try:
      return rule.endpoint(environ, custom_start_response, **values)
    except HTTPException as e:
      return e.get_response(environ)(environ, custom_start_response)
    except Exception as e:
      log.exception('Unknown error occurred processing request')
      return InternalServerError(
          description='Unknown error occurred',
          original_exception=e).get_response(environ)(environ,
                                                      custom_start_response)

  def _server_thread(self):
    log.info(f'Starting webserver on {self.bind_hostname}:{self.bind_port}')
    app = self._handler
    app = DispatcherMiddleware(app, self.mount_map)
    app = WSGILogger(app)
    self.server = WSGIServer((self.bind_hostname, self.bind_port), app)
    self.server.stats['Enabled'] = True
    self.server.start()

  @execute()
  def run(self):
    t = Thread(target=self._server_thread, name='Webserver')
    t.start()
    return t

  @on_shutdown()
  def on_shutdown(self):
    log.info('Shutting down webserver')
    if self.server:
      self.server.stop()
    log.info('Successfully shut down webserver')


class _EndpointConfiguration(NamedTuple):
  rules: Rule
  wrap: bool


def endpoint(rules: Union[Rule, Collection[Rule]], wrap: bool = True) -> Any:
  if isinstance(rules, Rule):
    rules = [rules]

  def decorator(function: Any):
    function.__endpoint__ = _EndpointConfiguration(rules=rules, wrap=wrap)
    return function

  return decorator


@singleton
class EndpointProcessor(DecoratorProcessor):
  injector: Injector = None
  web_server: WebServer = None

  @inject
  def __init__(self, injector: Injector, web_server: WebServer) -> None:
    super().__init__()
    self.injector = injector
    self.web_server = web_server

  def _wrap_request_response(self, fun) -> Callable:

    def f(environ, start_response, **kwargs):
      request = Request(environ)
      response = fun(request, **kwargs)
      return response(environ, start_response)

    return f

  def process(self, bindings: List[Any]) -> None:
    for interface, ep, fun in self.methods_by_decorated_name(
        bindings, 'endpoint'):
      full_fun_name = f'{interface.__module__}.{interface.__name__}.{fun.__name__}'
      log.info(f'Discovered endpoints on {full_fun_name} with rules {ep.rules}')
      wrapped_fun = DecoratorProcessor.wrap_function(
          self.injector.get(interface), fun, self.injector)
      if ep.wrap:
        wrapped_fun = self._wrap_request_response(wrapped_fun)
      for rule in ep.rules:
        for method in rule.methods:
          if method == 'HEAD':
            # Ignore HEAD method to reduce noise.
            continue
          # Initialize metric for the given endpoint.
          framework_webserver_endpoint_requests_z.labels(
              rule=rule.rule, method=method, status=200)
        rule.endpoint = wrapped_fun
        # TODO(rhollander): Cleanup this dependency.
        # The result of process() should be used in a provider to inject the List[Rule]
        # into the WebServer on startup. This requires changes to how DecoratorProcessors
        # work.
        self.web_server.url_map.add(rule)


class _WebServerImplModule(Module):

  def configure(self, binder: Binder):
    binder.bind(EndpointProcessor)
    binder.bind(WebServer)

  @multiprovider
  def provide_decorator_processor(
      self, endpoint_processor: EndpointProcessor) -> List[DecoratorProcessor]:
    return [endpoint_processor]

  @multiprovider
  def provide_default_webapp_list(self) -> List[WebApp]:
    # Provide default empty list of web applications to make injector happy.
    return []


class WebServerModule(Module):

  def configure(self, binder: Binder):
    if FLAGS.webserver_bind_hostname and FLAGS.webserver_bind_port:
      binder.bind(_WebserverBindHostnameKey, to=FLAGS.webserver_bind_hostname)
      binder.bind(_WebserverBindPortKey, to=FLAGS.webserver_bind_port)
      binder.install(_WebServerImplModule)
