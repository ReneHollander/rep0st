from injector import Module, ProviderOf, inject
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import Session, relationship

from rep0st.config.rep0st_database import Rep0stDatabaseModule
from rep0st.db import Base, PostType
from rep0st.framework.data.repository import CompoundKey, Repository


class FeatureVectorRepositoryModule(Module):

  def configure(self, binder):
    binder.install(Rep0stDatabaseModule)
    binder.bind(FeatureVectorRepository)


class FeatureVector(Base):
  __tablename__ = 'feature_vector'
  post_id = Column(
      Integer,
      ForeignKey('post.id'),
      primary_key=True,
      index=True,
      autoincrement=False)
  post = relationship('Post', back_populates='feature_vectors')
  id = Column(Integer, primary_key=True, index=True)
  # Same as post.type. Needed for better index.
  post_type = Column(Enum(PostType), nullable=False, index=True)
  vec = Column(Vector(108))

  def __str__(self):
    return "FeatureVector(post=%s, post_type=%s, vec=%s)" % (
        self.post, self.post_type, self.vec)

  def __repr__(self):
    return f"FeatureVector(post_id={self.post_id}, post_type={self.post_type}, id={self.id})"


class FeatureVectorKey(CompoundKey):
  post_id: int
  id: int
  post_type: PostType


class FeatureVectorRepository(Repository[FeatureVectorKey, FeatureVector]):

  indices = [
      Index(
          'feature_vector_post_type_image_vec_approx',
          FeatureVector.vec,
          postgresql_using='hnsw',
          postgresql_with={
              'm': 16,
              'ef_construction': 64
          },
          postgresql_ops={'vec': 'vector_l2_ops'},
          postgresql_where=FeatureVector.post_type == PostType.IMAGE,
      )
  ]

  @inject
  def __init__(self, session_provider: ProviderOf[Session]) -> None:
    super().__init__(FeatureVectorKey, FeatureVector, session_provider)
