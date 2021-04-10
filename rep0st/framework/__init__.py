from typing import Any, List

import enum

from absl import flags
from injector import Binder, Injector, Module

FLAGS = flags.FLAGS


class Environment(enum.Enum):
  DEVELOPMENT = 'DEVELOPMENT'
  PRODUCTION = 'PRODUCTION'


flags.DEFINE_enum_class('environment', Environment.PRODUCTION, Environment,
                        'Environment this application is running in.')


class EnvironmentModule(Module):

  def configure(self, binder: Binder) -> None:
    binder.bind(Environment, to=FLAGS.environment)


def get_bindings(injector: Injector) -> List[Any]:
  if not injector:
    return []

  return list(injector.binder._bindings.keys()) + get_bindings(injector.parent)
