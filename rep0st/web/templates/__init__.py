from pathlib import Path
from typing import NewType

import jinja2
from absl import flags
from injector import Binder, Module, provider, singleton
from jinja2 import FileSystemLoader, Template, select_autoescape

from rep0st.framework import Environment
from rep0st.framework.app import COMMIT_SHA

IndexTemplate = NewType('IndexTemplate', Template)

FLAGS = flags.FLAGS
flags.DEFINE_string(
    'google_analytics_measurement_id', None,
    'When set, adds a GA snippet to all pages reporting statistics to the given measurement ID.'
)


class _TemplateEnvironment(jinja2.Environment):

  def __init__(self, env: Environment):
    args = {}
    args.update(auto_reload=False)
    if env == Environment.DEVELOPMENT:
      args.update(cache_size=0, auto_reload=True)

    super(_TemplateEnvironment, self).__init__(
        loader=FileSystemLoader(Path(__file__).parent.absolute()),
        autoescape=select_autoescape(),
        **args)
    self.globals['FRAMEWORK_BUILD_INFO'] = {'git_sha': COMMIT_SHA}
    if FLAGS.google_analytics_measurement_id:
      self.globals['GA'] = {
          'measurement_id': FLAGS.google_analytics_measurement_id
      }


class TemplateModule(Module):

  def configure(self, binder: Binder):
    pass

  @provider
  @singleton
  def provide_environment(self, env: Environment) -> jinja2.Environment:
    return _TemplateEnvironment(env)

  @provider
  def provide_index_template(self,
                             environment: jinja2.Environment) -> IndexTemplate:
    return environment.get_template('index.html')
