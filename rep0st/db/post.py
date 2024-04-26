import enum
import logging
from itertools import groupby
from typing import List, Optional

from injector import Module, ProviderOf, inject
from sqlalchemy import Boolean, Column, DateTime, Enum, Index, Integer, String, and_, func
from sqlalchemy.orm import Query, Session, relationship

from rep0st.config.rep0st_database import Rep0stDatabaseModule
from rep0st.db import Base
from rep0st.db.feature import Feature
from rep0st.framework.data.repository import Repository
from rep0st.framework.data.transaction import transactional

log = logging.getLogger(__name__)


class PostRepositoryModule(Module):

  def configure(self, binder):
    binder.install(Rep0stDatabaseModule)
    binder.bind(PostRepository)


class Type(enum.Enum):
  IMAGE = 'IMAGE'
  ANIMATED = 'ANIMATED'
  VIDEO = 'VIDEO'
  UNKNOWN = 'UNKNOWN'


def post_type_from_media_path(path: str) -> Type:
  ending = path[path.rfind('.') + 1:].lower()
  if ending in ['jpg', 'jpeg', 'png']:
    return Type.IMAGE
  elif ending in ['gif']:
    return Type.ANIMATED
  elif ending in ['mp4', 'webm']:
    return Type.VIDEO
  else:
    log.error(f'Could not deduce post type from {path} with ending {ending}')
    return Type.UNKNOWN


class Flag(enum.Enum):
  SFW = 'sfw'
  NSFW = 'nsfw'
  NSFL = 'nsfl'
  NSFP = 'nsfp'
  POL = 'pol'


class PostErrorStatus(enum.Enum):
  # No media was found on pr0gramm servers.
  NO_MEDIA_FOUND = 'NO_MEDIA_FOUND'
  # The downloaded media cannot be read.
  MEDIA_BROKEN = 'MEDIA_BROKEN'


class Post(Base):
  from rep0st.db.feature import Feature
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
  user = Column(String(32), nullable=False)
  # Type of the media in the post.
  # - IMAGE: Static images. (jpg, png)
  # - ANIMATED: Animated images. (gif)
  # - VIDEO: Videos. (mp4, webm)
  type = Column(Enum(Type), nullable=False, index=True)
  # Error status of the post.
  error_status = Column(Enum(PostErrorStatus), nullable=True, index=True)
  # True if the post is deleted on pr0gramm.
  deleted = Column(Boolean(), nullable=False, default=False)
  # List of features associated with this post.
  features = relationship(Feature)
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
        'is_pol': self.is_pol(),
        'image': self.image,
        'thumb': self.thumb,
        'fullsize': self.fullsize,
    }

  def as_indexed_doc(self):

    def feauture_key_func(feature: Feature):
      return feature.id

    return {
        'meta': {
            'id': self.id
        },
        'created':
            int(self.created.timestamp() * 1000),
        'flags': [flag.value for flag in self.get_flags()],
        'type':
            self.type.value,
        'tags': [tag.tag for tag in self.tags],
        'frames': [{
            'id': key,
            'features': {
                v.type: v.data for v in valuesiter
            }
        } for key, valuesiter in groupby(
            sorted(self.features, key=feauture_key_func), key=feauture_key_func)
                  ],
    }

  def is_sfw(self):
    return self.flags & 1 != 0

  def is_nsfw(self):
    return self.flags & 2 != 0

  def is_nsfl(self):
    return self.flags & 4 != 0

  def is_nsfp(self):
    return self.flags & 8 != 0

  def is_pol(self):
    return self.flags & 16 != 0

  def get_flags(self) -> List[Flag]:
    flags = []
    if self.is_sfw():
      flags.append(Flag.SFW)
    if self.is_nsfw():
      flags.append(Flag.NSFW)
    if self.is_nsfl():
      flags.append(Flag.NSFL)
    if self.is_nsfp():
      flags.append(Flag.NSFP)
    if self.is_pol():
      flags.append(Flag.POL)
    return flags

  def get_flag_by_importance(self) -> Flag:
    if self.is_nsfl():
      return Flag.NSFL
    if self.is_nsfw():
      return Flag.NSFW
    if self.is_nsfp():
      return Flag.NSFP
    if self.is_pol():
      return Flag.POL
    return Flag.SFW

  def __str__(self):
    return "Post(id=" + str(self.id) + ")"

  def __repr__(self):
    return "Post(id=" + str(self.id) + ")"


class PostRepository(Repository[int, Post]):

  indices = [
      # Index on error_status, type and deleted for fast missing feature lookups.
      Index('post_error_status_type_deleted_index', Post.error_status,
            Post.type, Post.deleted),
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
  def get_posts_missing_features(self, type: Optional[Type] = None):
    session = self._get_session()
    q = session.query(Post).join(Post.features, isouter=True)
    if type:
      q = q.filter(Post.type == type)
    return q.filter(
        and_(Post.error_status == None, Post.deleted == False,
             Feature.id == None))

  @transactional()
  def post_count(self) -> int:
    session = self._get_session()
    return session.query(func.count(Post.id)).scalar()

  @transactional()
  def get_latest_post_id_with_features(self) -> int:
    session = self._get_session()
    id = session.query(func.max(Post.id)).join(Post.features).filter(
        and_(Post.type == Type.IMAGE)).scalar()
    return 0 if id is None else id

  @transactional()
  def post_count_with_features(self) -> int:
    session = self._get_session()
    id = session.query(func.count(Post.id)).join(Post.features).filter(
        and_(Post.type == Type.IMAGE)).scalar()
    return 0 if id is None else id
