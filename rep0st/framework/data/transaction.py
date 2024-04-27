import functools
import logging
from threading import local
from typing import Any, Callable, List

from injector import Binder, Module, ProviderOf, inject, multiprovider, singleton
from sqlalchemy.orm import Session

from rep0st.framework.data.database import DatabaseSessionFactory
from rep0st.framework.decorator import DecoratorProcessor

log = logging.getLogger(__name__)


class _TransactionalConfiguration:
  name: str = None
  database_session_provider: ProviderOf[Session] = None
  database_session_factory_provider: ProviderOf[DatabaseSessionFactory] = None


transactional_state = local()


def transactional(autoflush: bool | None = None) -> Any:

  def decorator(fun: Callable):
    transactional_configuration = _TransactionalConfiguration()

    @functools.wraps(fun)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
      if not hasattr(transactional_state, 'depth'):
        transactional_state.depth = 0
      session = transactional_configuration.database_session_provider.get()
      if not transactional_state.depth:
        log.debug(
            f'Starting transaction on method {transactional_configuration.name}'
        )
        # Session start. Implicit with transactional_configuration.injector.get(DatabaseSession)
        pass
      autoflush_state = session.autoflush
      if autoflush is not None:
        session.autoflush = autoflush
      transactional_state.depth += 1
      try:
        ret = fun(*args, **kwargs)
        transactional_state.depth -= 1
        if transactional_state.depth == 0:
          log.debug(
              f'Committing transaction on method {transactional_configuration.name}'
          )
          # We reached the outer most @transactional(). Commit the transaction.
          session.commit()
      except:
        transactional_state.depth -= 1
        if transactional_state.depth == 0:
          log.info(
              f'Rolling back transaction on method {transactional_configuration.name}'
          )
          # We reached the outer most @transactional(). Rollback the transaction.
          session.rollback()
        raise
      finally:
        if transactional_state.depth == 0:
          log.debug(
              f'Removing session on method {transactional_configuration.name}')
          # Close the session, to remove invalid state in case of errors.
          session.close()
          # We reached the outer most @transactional(). Close the session.
          session_factory = transactional_configuration.database_session_factory_provider.get(
          )
          session_factory.remove()
          delattr(transactional_state, 'depth')
      if autoflush is not None:
        session.autoflush = autoflush_state
      return ret

    wrapper.__transactional__ = transactional_configuration
    return wrapper

  return decorator


@singleton
class TransactionalProcessor(DecoratorProcessor):

  @inject
  def __init__(
      self, database_session_provider: ProviderOf[Session],
      database_session_factory_provider: ProviderOf[DatabaseSessionFactory]
  ) -> None:
    super().__init__()
    self.database_session_provider = database_session_provider
    self.database_session_factory_provider = database_session_factory_provider

  def process(self, bindings: List[Any]) -> None:
    for interface, transactional_configuration, fun in self.methods_by_decorated_name(
        bindings, 'transactional'):
      full_fun_name = f'{interface.__module__}.{interface.__class__.__name__}.{fun.__name__}'
      log.debug(f'Discovered method {full_fun_name} for transactional')
      transactional_configuration.name = full_fun_name
      transactional_configuration.database_session_provider = self.database_session_provider
      transactional_configuration.database_session_factory_provider = self.database_session_factory_provider


class TransactionalModule(Module):

  def configure(self, binder: Binder) -> None:
    binder.bind(TransactionalProcessor)

  @multiprovider
  def provide_decorator_processor(
      self, transactional_processor: TransactionalProcessor
  ) -> List[DecoratorProcessor]:
    return [transactional_processor]
