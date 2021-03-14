import logging
import types
from threading import Thread
from typing import Any, Callable, Iterator, List, NamedTuple, Tuple, Type

from injector import Binder, Injector, Module, inject, multiprovider, singleton

from rep0st.framework.decorator import DecoratorProcessor

log = logging.getLogger(__name__)


class _ExecuteConfiguration(NamedTuple):
  order: float


def execute(order: float = 0) -> Any:

  def decorator(function: Any):
    function.__execute__ = _ExecuteConfiguration(order)
    return function

  return decorator


@singleton
class ExecuteProcessor(DecoratorProcessor):
  injector: Injector
  methods: List[Callable[[], None]] = []

  @inject
  def __init__(self, injector: Injector) -> None:
    super().__init__()
    self.injector = injector

  def process(self, bindings: List[Any]) -> None:
    methods: List[Tuple[float, Callable[[], None]]] = []

    found: Iterator[Tuple[Type, _ExecuteConfiguration,
                          Callable[[Any],
                                   Any]]] = self.methods_by_decorated_name(
                                       bindings, 'execute')
    for interface, execute_configuration, fun in found:
      log.info("Discovered method %s.%s with order %f for execution",
               interface.__module__, fun.__name__, execute_configuration.order)
      methods.append((execute_configuration.order,
                      types.MethodType(fun, self.injector.get(interface))))

    methods.sort(key=lambda tup: tup[0])
    self.methods = [tup[1] for tup in methods]

  def run_and_wait(self):
    log.debug("Executing methods marked @execute()")
    threads = []
    for method in self.methods:
      log.info("Executing method %s", method.__name__)
      ret = method()
      if isinstance(ret, Thread):
        threads.append(ret)
    for thread in threads:
      log.info("Joining Thread %s", thread.name)
      thread.join()


class ExecuteModule(Module):

  def configure(self, binder: Binder):
    binder.bind(ExecuteProcessor)

  @multiprovider
  def provide_decorator_processor(
      self, execute_processor: ExecuteProcessor) -> List[DecoratorProcessor]:
    return [execute_processor]
