import datetime
import importlib
import logging
import os
import sys
from typing import List, Any, Callable
import warnings

from absl import app, flags
from injector import Injector
import logstash_formatter
from prometheus_client import Info

from rep0st.framework import Environment, EnvironmentModule, get_bindings
from rep0st.framework.decorator import DecoratorProcessorModule, DecoratorProcessorRunner
from rep0st.framework.execute import ExecuteModule, ExecuteProcessor
from rep0st.framework.signal_handler import OnShutdownProcessor, SignalHandlerModule
from rep0st.framework.status_page.metricz import MetriczPageModule
from rep0st.framework.web import request_data

COMMIT_BRANCH = os.environ.get('COMMIT_BRANCH', 'no_branch')
COMMIT_SHA = os.environ.get('COMMIT_SHA', 'no_sha')
build_git_branch = Info(
    'build_git',
    'Info about this build, filled with data about the git repository.')
build_git_branch.info({'sha': COMMIT_SHA, 'branch': COMMIT_BRANCH})

log = logging.getLogger(__name__)
FLAGS = flags.FLAGS


def _makeRecordPatch(self,
                     name,
                     level,
                     fn,
                     lno,
                     msg,
                     args,
                     exc_info,
                     func=None,
                     extra=None,
                     sinfo=None):
  """Patch Logger.makeRecord to allow setting of file and lineno."""
  rv = logging._logRecordFactory(name, level, fn, lno, msg, args, exc_info,
                                 func, sinfo)
  if extra is not None:
    for key in extra:
      rv.__dict__[key] = extra[key]
  return rv


logging.Logger.makeRecord = _makeRecordPatch  # type: ignore


class Formatter(logging.Formatter):

  def formatMessage(self, record: logging.LogRecord) -> str:
    request_id = ''
    if hasattr(record, 'request_id'):
      request_id = f'[{record.request_id}] '
    ts = datetime.datetime.utcfromtimestamp(record.created)
    name = record.name
    if len(name) > 24:
      parts = name.split('.')
      reduction = 0
      for i, p in enumerate(parts):
        parts[i] = p[0]
        reduction += len(p) - 1
        if len(name) - reduction <= 24:
          break
      name = '.'.join(parts)

    location = f'{record.filename}:{record.lineno}'
    return f'{ts.isoformat()} {record.levelname:<8} [{record.threadName:<20}] [{name:<24}] [{location:<24}] {request_id}{record.getMessage()}'


_formatters = {
    'default': Formatter(),
    'logstash': logstash_formatter.LogstashFormatter(),
}
flags.DEFINE_enum('logtype', 'default', _formatters.keys(),
                  'Select the logtype to use.')
flags.DEFINE_enum('loglevel', 'DEBUG',
                  logging.getLevelNamesMapping().keys(),
                  'Select the loglevel to use.')


class AppendExtra(logging.Filter):

  def filter(self, record):
    if request_data.id:
      record.request_id = request_data.id
    return True


def setup_logging(logtype, loglevel):
  logging.captureWarnings(True)

  def log_warning(message, category, filename, lineno, file=None, line=None):
    logging.getLogger(category.__name__).log(
        logging.WARNING, message, extra=dict(lineno=lineno, filename=filename))

  warnings.showwarning = log_warning

  root = logging.getLogger()
  root.handlers = []
  root.setLevel(loglevel)
  handler = logging.StreamHandler(sys.stdout)
  handler.addFilter(AppendExtra())
  handler.setFormatter(_formatters[logtype])
  root.addHandler(handler)

  urllib3_connectionpool_logger = logging.getLogger('urllib3.connectionpool')
  urllib3_connectionpool_logger.setLevel(logging.INFO)


def setup():
  logtype = 'default'
  loglevel = logging.DEBUG
  for arg in sys.argv[1:]:
    if arg.startswith('--logtype='):
      logtype = arg[10:]
    if arg.startswith('--loglevel='):
      loglevel = arg[11:]
  setup_logging(logtype, loglevel)


setup()


def _pre_absl(modules_func: Callable[[], List[Any]]):
  """Stuff to setup before absl is run."""
  log.info('Starting application')
  log.info('Current working directory:')
  log.info(f"  '{os.getcwd()}'")
  log.info('Arguments passed to the application:')
  for arg in sys.argv:
    log.info(f"  '{arg}")
  log.info('Environment passed to the application:')
  for key, val in os.environ.items():
    log.info(f"  '{key}={val}'")

  return _post_absl(modules_func)


def _load_injector_module(name: str):
  pymodule, pyclass = name.rsplit('.', 1)
  m = importlib.import_module(pymodule)
  c = getattr(m, pyclass, None)
  if not c:
    raise ImportError(f'Module with name {name} not found.')
  log.info(f'Loaded module {c.__name__}')
  return c


def _post_absl(modules_func: Callable[[], List[Any]]):

  def main(argv: Any):
    """Stuff to setup after absl is run."""
    setup_logging(FLAGS.logtype, FLAGS.loglevel)

    try:
      modules = modules_func()
      modules.insert(0, EnvironmentModule)
      modules.insert(0, DecoratorProcessorModule)
      modules.insert(0, SignalHandlerModule)
      modules.insert(0, ExecuteModule)
      modules.insert(0, MetriczPageModule)
      injector = Injector(modules=modules, auto_bind=False)

      env = injector.get(Environment)
      log.info(f'Application running with environment {env.name}')

      bindings = get_bindings(injector)
      for binding in bindings:
        try:
          log.debug(f'Resolving binding for {binding}')
          injector.get(binding)
        except:
          log.exception(
              f'Could not start application: Error resolving binding {binding}')
          return 1

      # Run all decorator processors.
      decorator_processor_runner = injector.get(DecoratorProcessorRunner)
      decorator_processor_runner.run_processors()

      # Run all execute methods and wait until all finished.
      execute_processor = injector.get(ExecuteProcessor)
      execute_processor.run_and_wait()
      # Everything that wanted to be executed finished.

      # Call the on_shutdown marked functions.
      on_shutdown_processor = injector.get(OnShutdownProcessor)
      on_shutdown_processor.handle_shutdown()

      log.info('Application finished successfully')
      return 0
    except:
      log.exception('Application finished with an error')
      return 1

  return main


def run(modules_func: Callable[[], List[Any]]):
  app.run(_pre_absl(modules_func))
