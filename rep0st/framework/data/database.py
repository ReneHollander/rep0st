import logging
from typing import NewType, TypeVar

from injector import Binder, Module, inject, provider, singleton
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import Session, scoped_session, sessionmaker

log = logging.getLogger(__name__)
DatabaseEngine = NewType('DatabaseEngine', object)
DatabaseSessionFactory = NewType('DatabaseSessionFactory', callable)
B = TypeVar('B')


class DatabaseModule(Module):
  url: URL
  base: B

  def __init__(self, url: URL, base: B):
    self.url = url
    self.base = base

  def configure(self, binder: Binder):
    from rep0st.framework.data.transaction import TransactionalModule
    binder.install(TransactionalModule)

  @provider
  @singleton
  def provide_database_engine(self) -> DatabaseEngine:
    engine = create_engine(self.url)
    self.base.metadata.create_all(engine)
    self.base.metadata.bind = engine
    return engine

  @inject
  @provider
  @singleton
  def provide_database_session_factory(
      self, database_engine: DatabaseEngine) -> DatabaseSessionFactory:
    return scoped_session(sessionmaker(database_engine))

  @inject
  @provider
  def provide_database_session(
      self, database_session_factory: DatabaseSessionFactory) -> Session:
    return database_session_factory()
