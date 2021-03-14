from typing import Any, Collection, Generic, NamedTuple, Type, TypeVar

from injector import ProviderOf
from sqlalchemy import func, inspect
from sqlalchemy.orm import Query, Session

from rep0st.framework.data.transaction import transactional

K = TypeVar('K')
V = TypeVar('V')


class CompoundKey(NamedTuple):
  pass


def _get_filter_from_comound_key(key: CompoundKey) -> dict[str, Any]:
  return {
      a: key.__getattribute__(a)
      for a in dir(key)
      if not a.startswith('__') and not callable(getattr(key, a))
  }


class Repository(Generic[K, V]):
  session_provider: ProviderOf[Session] = None

  def __init__(self, k_type: Type[K], v_type: Type[V],
               session_provider: ProviderOf[Session]) -> None:
    self._k_type = k_type
    self._v_type = v_type
    self.session_provider = session_provider

  def _get_session(self) -> Session:
    return self.session_provider.get()

  @transactional()
  def add(self, value: V) -> V:
    session = self._get_session()
    session.add(value)
    return value

  @transactional()
  def add_all(self, values: Collection[V]) -> Collection[V]:
    session = self._get_session()
    session.add_all(values)
    return values

  @transactional()
  def persist(self, value: V) -> V:
    session = self._get_session()
    session.add(value)
    session.flush()
    return value

  @transactional()
  def persist_all(self, values: Collection[V]) -> Collection[V]:
    session = self._get_session()
    session.add_all(values)
    session.flush()
    return values

  @transactional()
  def persist_bulk(self, values: Collection[V]):
    session = self._get_session()
    session.bulk_save_objects(values)

  def _get_primary_key(self):
    return inspect(self._v_type).primary_key[0].name

  @transactional()
  def get_by_id(self, key: K) -> Query:
    session = self._get_session()
    key_filter = {
        self._get_primary_key(): key,
    }
    if issubclass(self._k_type, CompoundKey):
      key_filter = _get_filter_from_comound_key(key)
    return session.query(self._v_type).filter_by(**key_filter)

  @transactional()
  def get_by_ids(self, keys: Collection[K]) -> Query:
    if issubclass(self._k_type, CompoundKey):
      raise NotImplementedError(
          "Repository.get_by_ids is not implemented for compound keys")
    session = self._get_session()
    return session.query(self._v_type).filter(
        getattr(self._v_type, self._get_primary_key()).in_(keys))

  @transactional()
  def count(self) -> int:
    session = self._get_session()
    return session.query(func.count()).scalar()

  @transactional()
  def merge(self, value: V) -> V:
    return self._get_session().merge(value)

  @transactional()
  def query(self) -> Query:
    return self._get_session().query(self._v_type)
