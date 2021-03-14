from injector import Module, ProviderOf, inject
from sqlalchemy import Column, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Session, relationship

from rep0st.config.rep0st_database import Rep0stDatabaseModule
from rep0st.db import Base
from rep0st.framework.data.repository import CompoundKey, Repository


class FeatureRepositoryModule(Module):

  def configure(self, binder):
    binder.install(Rep0stDatabaseModule)
    binder.bind(FeatureRepository)


class Feature(Base):
  __tablename__ = 'feature'
  post_id = Column(
      Integer,
      ForeignKey('post.id'),
      primary_key=True,
      index=True,
      autoincrement=False)
  post = relationship('Post', back_populates='features')
  type = Column(String(32), nullable=False, primary_key=True, index=True)
  id = Column(Integer, primary_key=True, index=True)
  data = Column(LargeBinary)

  def __str__(self):
    return "Feature(post=%s, type=%s, data=%s)" % (self.post, self.type,
                                                   self.data)

  def __repr__(self):
    return f"Feature(post_id={self.post_id}, type={self.type}, id={self.id})"


class FeatureKey(CompoundKey):
  post_id: int
  type: str
  id: int


class FeatureRepository(Repository[FeatureKey, Feature]):

  @inject
  def __init__(self, session_provider: ProviderOf[Session]) -> None:
    super().__init__(FeatureKey, Feature, session_provider)
