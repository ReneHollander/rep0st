import logging
import signal
import time
import types
import os
from collections import namedtuple
from threading import Thread
from typing import Any, Callable, Dict, Iterator, List, Tuple, Type

from injector import Binder, Injector, Module, inject, multiprovider, singleton

from rep0st.framework.decorator import DecoratorProcessor

log = logging.getLogger(__name__)

_OnShutdownConfiguration = namedtuple('_OnShutdownConfiguration', '')


def on_shutdown() -> Any:

  def decorator(function: Any):
    function.__on_shutdown__ = _OnShutdownConfiguration()
    return function

  return decorator


@singleton
class SignalHandler:
  handlers: Dict[int, List[Callable[[], None]]] = {}

  def register_handler(self, signum: int, fun: Callable[[], None]):
    if not signum in self.handlers:
      self.handlers[signum] = []
      signal.signal(signum, self._signal_handler)
    self.handlers[signum].append(fun)

  def remove_all_handlers(self):
    self.handlers = {}

  def _signal_handler(self, signum, frame):
    log.info("Signal %s(%d) detected. Calling handlers.",
             signal.Signals(signum).name, signum)
    if signum in self.handlers:
      if signum not in self.handlers:
        return
      for fun in self.handlers[signum]:
        fun()


@singleton
class OnShutdownProcessor(DecoratorProcessor):
  injector: Injector
  methods: List[Callable[[], None]] = []
  signal_handler: SignalHandler

  @inject
  def __init__(self, injector: Injector, signal_handler: SignalHandler) -> None:
    super().__init__()
    self.injector = injector
    self.signal_handler = signal_handler
    self.signal_handler.register_handler(signal.SIGTERM, self.handle_shutdown)
    self.signal_handler.register_handler(signal.SIGINT, self.handle_shutdown)
    self.signal_handler.register_handler(signal.SIGQUIT, self.handle_shutdown)

  def process(self, bindings: List[Any]) -> None:
    found: Iterator[Tuple[Type, _OnShutdownConfiguration,
                          Callable[[Any],
                                   Any]]] = self.methods_by_decorated_name(
                                       bindings, 'on_shutdown')
    for interface, on_shutdown_configuration, fun in found:
      full_fun_name = "{}.{}.{}".format(interface.__module__,
                                        interface.__class__.__name__,
                                        fun.__name__)
      log.info("Discovered method %s for on_shutdown", full_fun_name)
      self.methods.append(types.MethodType(fun, self.injector.get(interface)))

  def _shutdown_watchdog(self):
    time.sleep(5)
    log.info("Timed out waiting for shutdown. Forcing it now... Goodbye!")
    self.signal_handler.remove_all_handlers()
    # Force terminate.
    os._exit(os.EX_SOFTWARE)

  def handle_shutdown(self):
    log.debug("Executing methods marked @on_shutdown()")
    thread = Thread(name='Shutdown watchdog', target=self._shutdown_watchdog)
    thread.start()
    for method in self.methods:
      method()


class SignalHandlerModule(Module):

  def configure(self, binder: Binder):
    binder.bind(SignalHandler)
    binder.bind(OnShutdownProcessor)

  @multiprovider
  def provide_decorator_processor(
      self,
      on_shutdown_processor: OnShutdownProcessor) -> List[DecoratorProcessor]:
    return [on_shutdown_processor]
