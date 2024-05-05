import enum
import logging
import math
from typing import List, Optional

from injector import Module, ProviderOf, inject
import numpy
from numpy.typing import NDArray
from sqlalchemy import Boolean, Column, DateTime, Enum, Index, Integer, String, and_, func, text
from sqlalchemy.orm import Query, Session, relationship

from rep0st.config.rep0st_database import Rep0stDatabaseModule
from rep0st.db import Base, PostType
from rep0st.db.feature import FeatureVector
from rep0st.framework.data.repository import Repository
from rep0st.framework.data.transaction import transactional

log = logging.getLogger(__name__)


class PostRepositoryModule(Module):

  def configure(self, binder):
    binder.install(Rep0stDatabaseModule)
    binder.bind(PostRepository)


def post_type_from_media_path(path: str) -> PostType:
  ending = path[path.rfind('.') + 1:].lower()
  if ending in ['jpg', 'jpeg', 'png']:
    return PostType.IMAGE
  elif ending in ['gif']:
    return PostType.ANIMATED
  elif ending in ['mp4', 'webm']:
    return PostType.VIDEO
  else:
    log.error(f'Could not deduce post type from {path} with ending {ending}')
    return PostType.UNKNOWN


class Flag(enum.Enum):
  SFW = 'sfw'
  NSFW = 'nsfw'
  NSFL = 'nsfl'
  NSFP = 'nsfp'
  POL = 'pol'


def flagbits_to_flags(bits: int) -> list[Flag]:
  flags = []
  if bits & 1 != 0:
    flags.append(Flag.SFW)
  if bits & 2 != 0:
    flags.append(Flag.NSFW)
  if bits & 4 != 0:
    flags.append(Flag.NSFL)
  if bits & 8 != 0:
    flags.append(Flag.NSFP)
  if bits & 16 != 0:
    flags.append(Flag.POL)


def flags_to_flagbits(flags: list[Flag]) -> int:
  bits = 0
  if Flag.SFW in flags:
    bits |= 1
  if Flag.NSFW in flags:
    bits |= 2
  if Flag.NSFL in flags:
    bits |= 4
  if Flag.NSFP in flags:
    bits |= 8
  if Flag.POL in flags:
    bits |= 16
  return bits


class PostErrorStatus(enum.Enum):
  # No media was found on pr0gramm servers.
  NO_MEDIA_FOUND = 'NO_MEDIA_FOUND'
  # The downloaded media cannot be read.
  MEDIA_BROKEN = 'MEDIA_BROKEN'


class Post(Base):
  from rep0st.db.feature import FeatureVector
  from rep0st.db.tag import Tag

  __tablename__ = 'post'
  # Post id.
  id = Column(Integer, primary_key=True, index=True, autoincrement=False)
  # Timestamp this post was created.
  created = Column(DateTime(), nullable=False)
  # Path of the image on pr0gramm servers.
  image = Column(String(256), nullable=False, index=True)
  # Path of the thumbnail on pr0gramm servers.
  thumb = Column(String(256), nullable=False)
  # Path of the fullsize image on pr0gramm servers. Optional.
  fullsize = Column(String(256))
  # Width of the media in pixels.
  width = Column(Integer(), nullable=False)
  # Height of the media in pixels.
  height = Column(Integer(), nullable=False)
  # True if the media has audio.
  audio = Column(Boolean(), nullable=False)
  # URL of the source of the image. Optional.
  source = Column(String(512))
  # Flags for the post encoded as a bitset. If the bit is set,
  # the post is marked with the given tag.
  # Bit 0: SFW
  # Bit 1: NSFW
  # Bit 2: NSFL
  # Bit 3: NSFP
  # Bit 4: POL
  flags = Column(Integer(), nullable=False)
  # Name of the user that uploaded the post.
  username = Column(String(32), nullable=False)
  # Type of the media in the post.
  # - IMAGE: Static images. (jpg, png)
  # - ANIMATED: Animated images. (gif)
  # - VIDEO: Videos. (mp4, webm)
  type = Column(Enum(PostType), nullable=False, index=True)
  # Error status of the post.
  error_status = Column(Enum(PostErrorStatus), nullable=True, index=True)
  # True if the post is deleted on pr0gramm.
  deleted = Column(Boolean(), nullable=False, default=False)
  # List of features associated with this post.
  feature_vectors = relationship(
      FeatureVector, cascade='save-update, merge, delete, delete-orphan')
  # True if features are indexed for this post.
  features_indexed = Column(
      Boolean(), nullable=False, index=True, default=False)
  # List of tags associated with this post.
  tags = relationship(Tag)

  def __json__(self):
    return {
        'id': self.id,
        'user': self.user,
        'created': self.created.isoformat(),
        'is_sfw': self.is_sfw(),
        'is_nsfw': self.is_nsfw(),
        'is_nsfl': self.is_nsfl(),
        'is_nsfp': self.is_nsfp(),
        'is_pol': self.is_pol(),
        'image': self.image,
        'thumb': self.thumb,
        'fullsize': self.fullsize,
    }

  def is_sfw(self):
    return Flag.SFW in self.get_flags()

  def is_nsfw(self):
    return Flag.NSFW in self.get_flags()

  def is_nsfl(self):
    return Flag.NSFL in self.get_flags()

  def is_nsfp(self):
    return Flag.NSFP in self.get_flags()

  def is_pol(self):
    return Flag.POL in self.get_flags()

  def get_flags(self) -> List[Flag]:
    return flagbits_to_flags(self.flags)

  def __str__(self):
    return "Post(id=" + str(self.id) + ")"

  def __repr__(self):
    return "Post(id=" + str(self.id) + ")"


class PostRepository(Repository[int, Post]):

  indices = [
      # Index on error_status, type and deleted and features_indexed for fast missing feature lookups.
      Index('post_error_status_type_deleted_features_indexed_index',
            Post.error_status, Post.type, Post.deleted, Post.features_indexed),
  ]

  @inject
  def __init__(self, session_provider: ProviderOf[Session]) -> None:
    super().__init__(int, Post, session_provider)

  @transactional()
  def get_latest_post_id(self) -> int:
    session = self._get_session()
    id = session.query(func.max(Post.id)).scalar()
    return 0 if id is None else id

  @transactional()
  def get_posts(self, type: Optional[str] = None) -> Query[Post]:
    session = self._get_session()
    if type is not None:
      return session.query(Post).filter(Post.type == type)
    else:
      return session.query(Post)

  @transactional()
  def get_posts_missing_features(self, type: Optional[PostType] = None):
    session = self._get_session()
    q = session.query(Post)
    if type:
      q = q.filter(Post.type == type)
    return q.filter(
        and_(Post.error_status == None, Post.deleted == False,
             Post.features_indexed == False)).order_by(Post.id)

  @transactional()
  def post_count(self) -> int:
    session = self._get_session()
    return session.query(func.count(Post.id)).scalar()

  @transactional()
  def get_latest_post_id_with_features(self) -> int:
    session = self._get_session()
    id = session.query(func.max(Post.id)).filter(
        and_(Post.features_indexed == True)).scalar()
    return 0 if id is None else id

  @transactional()
  def post_count_with_features(self) -> int:
    session = self._get_session()
    id = session.query(func.count(Post.id)).filter(
        and_(Post.features_indexed == True)).scalar()
    return 0 if id is None else id

  @transactional()
  def search_posts(self,
                   type: PostType,
                   feature_vector: NDArray[numpy.float32],
                   flags: list[Flag] | None = None,
                   exact: bool | None = False,
                   ef_search: int | None = None) -> Query[Post]:
    session = self._get_session()
    if exact:
      session.connection().execute(text('SET enable_indexscan = off'))
    if ef_search:
      session.connection().execute(text(f'SET hnsw.ef_search = {ef_search}'))
    q = session.query(
        # The largest distance between two feature_vectors can be sqrt(108),
        # since each dimension has a value between 0..1.
        # So to calculate similarity divide by the max value and then subtract
        # from 1 to get a percentage similarity.
        (1 - (FeatureVector.vec.l2_distance(feature_vector) / math.sqrt(108))
        ).label('score'),
        Post).join(Post.feature_vectors).filter(
            FeatureVector.post_type == type).order_by(
                FeatureVector.vec.l2_distance(feature_vector))
    if flags:
      q = q.filter(Post.flags.op('&')(flags_to_flagbits(flags)) > 0)
    return q
