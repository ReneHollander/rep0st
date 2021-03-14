import functools
import inspect
import logging
import types
from abc import ABC, abstractmethod
from typing import Any, Callable, Iterator, List, Tuple, Type, TypeVar

from injector import Injector, Module, inject, singleton

from rep0st.framework import get_bindings

log = logging.getLogger(__name__)
T = TypeVar('T')


class DecoratorProcessor(ABC):

  @abstractmethod
  def process(self, bindings: List[Any]) -> None:
    pass

  def methods_by_decorated_name(
      self, bindings: List[Any],
      search_name: str) -> Iterator[Tuple[Type, T, Callable[[Any], Any]]]:
    for binding in bindings:
      interface = binding
      for name, fun in inspect.getmembers(interface):
        data = getattr(fun, '__' + search_name + '__', None)
        if data is not None:
          yield (interface, data, fun)

  @staticmethod
  def wrap_function(instance: Any, fun: Callable,
                    injector: Injector) -> Callable:
    fun = types.MethodType(fun, instance)

    @functools.wraps(fun)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
      return injector.call_with_injection(
          callable=fun, args=args, kwargs=kwargs)

    return wrapper  # type: ignore


@singleton
class DecoratorProcessorRunner:
  injector: Injector
  decorator_processors: List[DecoratorProcessor]

  @inject
  def __init__(
      self, injector: Injector,
      decorator_processors: List[DecoratorProcessor]) -> None:  # type: ignore
    self.injector = injector
    self.decorator_processors = decorator_processors

  def _get_all_bindings(self) -> List[Any]:
    return get_bindings(self.injector)

  def run_processors(self):
    for decorator_processor in set(self.decorator_processors):
      log.debug("Running decorator processor %s",
                decorator_processor.__class__.__name__)
      decorator_processor.process(bindings=self._get_all_bindings())


class DecoratorProcessorModule(Module):

  def configure(self, binder):
    binder.bind(DecoratorProcessorRunner)
