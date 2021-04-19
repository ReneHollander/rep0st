import sys

from absl.flags import ArgumentParser, ArgumentSerializer, DEFINE_flag, DEFINE_string, FlagValues
from absl.flags import Flag
from injector import Binder, Injector, Module, SingletonScope, inject, singleton

from rep0st.framework import get_bindings

class AppFlag:
  pass


def DeclareStringFlag(name, default, help, required=False):
  @singleton
  class NewFlag(AppFlag):
    @inject
    def __init__(self, flag_values: FlagValues):
      self.flag_values = flag_values

    def get(self):
      return self.flag_values.__getattr__(name)

  NewFlag.__name__ = f'Flag.{name}'
  NewFlag.__qualname__ = f'Flag.{name}'
  NewFlag.__flag__ = Flag(ArgumentParser(), ArgumentSerializer(), name, default, help)
  NewFlag.__required__ = required
  return NewFlag


class FlagValuesModule(Module):
  def __init__(self, flag_values: FlagValues):
    self.flag_values = flag_values

  def configure(self, binder: Binder) -> None:
    binder.bind(FlagValues, to=self.flag_values, scope=SingletonScope)


def do(modules):
  fv = FlagValues()

  DEFINE_string('logger', 'megalogger', 'Configure the logger to use', flag_values=fv)

  fv(sys.argv, known_only=True)

  fv.unparse_flags()

  injector = Injector([FlagValuesModule(fv)] + modules)

  for binding in get_bindings(injector):
    if issubclass(binding, AppFlag):
      DEFINE_flag(binding.__flag__, fv,
                  None, binding.__required__)

  fv(sys.argv)

  return injector
