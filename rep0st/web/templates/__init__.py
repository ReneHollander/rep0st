from pathlib import Path
from typing import NewType

from absl import flags
from injector import Binder, Module, provider
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from rep0st.framework.app import COMMIT_SHA

IndexTemplate = NewType('IndexTemplate', Template)

FLAGS = flags.FLAGS
flags.DEFINE_string(
    'google_analytics_measurement_id', None,
    'When set, adds a GA snippet to all pages reporting statistics to the given measurement ID.'
)


class _TemplateEnvironment(Environment):

  def __init__(self, **kwargs):
    super(_TemplateEnvironment, self).__init__(
        loader=FileSystemLoader(Path(__file__).parent.absolute()),
        autoescape=select_autoescape(),
        **kwargs)
    self.globals['FRAMEWORK_BUILD_INFO'] = {'git_sha': COMMIT_SHA}
    if FLAGS.google_analytics_measurement_id:
      self.globals['GA'] = {
          'measurement_id': FLAGS.google_analytics_measurement_id
      }


class TemplateModule(Module):

  def configure(self, binder: Binder):
    pass

  @provider
  def provide_environment(self) -> Environment:
    return _TemplateEnvironment()

  @provider
  def provide_index_template(self, environment: Environment) -> IndexTemplate:
    return environment.get_template('index.html')
