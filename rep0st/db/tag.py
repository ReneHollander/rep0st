from injector import Module, ProviderOf, inject
from sqlalchemy import Column, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Session, relationship

from rep0st.config.rep0st_database import Rep0stDatabaseModule
from rep0st.db import Base
from rep0st.framework.data.repository import Repository
from rep0st.framework.data.transaction import transactional


class TagRepositoryModule(Module):

  def configure(self, binder):
    binder.install(Rep0stDatabaseModule)
    binder.bind(TagRepository)


class Tag(Base):
  __tablename__ = 'tag'
  id = Column(Integer, primary_key=True, index=True, autoincrement=False)
  post_id = Column(Integer, ForeignKey('post.id'), nullable=False, index=True)
  post = relationship('Post', back_populates="tags")
  tag = Column(String(256), nullable=False, index=True)
  up = Column(Integer, nullable=False)
  down = Column(Integer, nullable=False)
  confidence = Column(Float, nullable=False, index=True)

  def __str__(self):
    return "Tag(id=%d, post_id=%d, tag=%s, up=%d, down=%d, confidence=%f)" % (
        self.id, self.post_id, self.tag, self.up, self.down, self.confidence)

  def __repr__(self):
    return self.__str__()


class TagRepository(Repository[int, Tag]):

  @inject
  def __init__(self, session_provider: ProviderOf[Session]) -> None:
    super().__init__(int, Tag, session_provider)

  @transactional()
  def get_latest_tag_id(self):
    session = self._get_session()
    id = session.query(func.max(Tag.id)).scalar()
    return 0 if id is None else id
