import enum

from logbook import Logger
from sqlalchemy import Column, Integer, DateTime, String, Boolean, func, LargeBinary, Enum, ForeignKey, Index, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

log = Logger('database')
Base = declarative_base()


class PostType(enum.Enum):
    IMAGE = 1
    ANIMATED = 2
    VIDEO = 3

    @staticmethod
    def fromImage(image):
        ending = image[image.rfind('.') + 1:]
        if ending in ['jpg', 'jpeg', 'png']:
            return PostType.IMAGE
        elif ending in ['gif']:
            return PostType.ANIMATED
        elif ending in ['mp4']:
            return PostType.VIDEO


class PostTypeTable(Base):
    __tablename__ = 'posttype'
    name = Column(Enum(PostType), primary_key=True, index=True)


class PostStatus(enum.Enum):
    NOT_INDEXED = 1
    INDEXED = 2
    BROKEN = 3


class Flag(enum.Enum):
    SFW = 1
    NSFW = 2
    NSFL = 3
    NSFP = 4


class Post(Base):
    __tablename__ = 'post'
    id = Column(Integer, primary_key=True, index=True)
    created = Column(DateTime(), nullable=False)
    image = Column(String(256), nullable=False, index=True)
    thumb = Column(String(256), nullable=False)
    fullsize = Column(String(256))
    width = Column(Integer(), nullable=False)
    height = Column(Integer(), nullable=False)
    audio = Column(Boolean(), nullable=False)
    source = Column(String(512))
    flags = Column(Integer(), nullable=False)
    user = Column(String(32), nullable=False)
    type = Column(Enum(PostType), nullable=False, index=True)
    status = Column(Enum(PostStatus), nullable=False, index=True, default=PostStatus.NOT_INDEXED)
    __table_args__ = (Index('post_status_type_index', "status", "type"),)

    def __json__(self):
        return {
            'id': self.id,
            'user': self.user,
            'created': self.created.isoformat(),
            'is_sfw': self.is_sfw(),
            'is_nsfw': self.is_nsfw(),
            'is_nsfl': self.is_nsfl(),
            'image': self.image,
            'thumb': self.thumb,
        }

    def is_sfw(self):
        return self.flags & 1 != 0

    def is_nsfw(self):
        return self.flags & 2 != 0

    def is_nsfl(self):
        return self.flags & 4 != 0

    def is_nsfp(self):
        return self.flags & 8 != 0

    def get_flags(self):
        flags = []
        if self.is_sfw():
            flags.append(Flag.SFW)
        if self.is_nsfw():
            flags.append(Flag.NSFW)
        if self.is_nsfl():
            flags.append(Flag.NSFL)
        if self.is_nsfp():
            flags.append(Flag.NSFP)
        return flags

    def get_flag_by_importance(self):
        if self.is_nsfl():
            return Flag.NSFL
        if self.is_nsfw():
            return Flag.NSFW
        if self.is_nsfp():
            return Flag.NSFP
        return Flag.SFW

    def __str__(self):
        return "Post(id=" + str(self.id) + ")"

    def __repr__(self):
        return "Post(id=" + str(self.id) + ")"


class FeatureType(enum.Enum):
    FEATURE_VECTOR = 1
    AHASH = 2
    PHASH = 3
    DHASH = 4
    WHASH = 5


class FeatureTypeTable(Base):
    __tablename__ = 'featuretype'
    name = Column(Enum(FeatureType), primary_key=True, index=True)


class Feature(Base):
    __tablename__ = 'feature'
    post_id = Column(Integer, ForeignKey('post.id'), primary_key=True, index=True)
    post = relationship(Post)
    type = Column(Enum(FeatureType), primary_key=True, index=True)
    id = Column(Integer, primary_key=True, index=True)
    data = Column(LargeBinary)

    def __str__(self):
        return "Feature(post=%s, type=%s, data=%s)" % (self.post, self.type, self.data)

    def __repr__(self):
        return "Feature(id=" + str(self.id) + ")"

    @staticmethod
    def from_analyzeresult(post, type, data):
        feature = Feature()
        feature.post_id = post.id
        feature.type = type
        feature.id = 1
        feature.data = data
        return feature


class Tag(Base):
    __tablename__ = 'tag'
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, nullable=False, index=True)
    tag = Column(String(256), nullable=False, index=True)
    up = Column(Integer, nullable=False)
    down = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False, index=True)

    def __str__(self):
        return "Tag(id=%d, post_id=%d, tag=%s, up=%d, down=%d, confidence=%f)" % (
            self.id, self.post_id, self.tag, self.up, self.down, self.confidence)

    def __repr__(self):
        return self.__str__()


class Database():
    def __init__(self, engine):
        self.engine = engine
        log.info("connecting to database {}", engine)
        Base.metadata.create_all(self.engine)
        Base.metadata.bind = self.engine
        self.DBSession = sessionmaker(bind=self.engine, expire_on_commit=False)
        log.info("connected to database {}", engine)

    def latest_post_id(self):
        session = self.DBSession()
        res = session.query(func.max(Post.id).label('latest_post_id')).scalar()
        session.close()
        return res

    def latest_tag_id(self):
        session = self.DBSession()
        res = session.query(func.max(Tag.id).label('latest_tag_id')).scalar()
        session.close()
        return res

    def get_engine(self):
        return self.engine

    def get_posts(self, type=None):
        session = self.DBSession()
        res = None
        if type is not None:
            res = session.query(Post).filter(Post.type == type)
        else:
            res = session.query(Post)
        session.close()
        return res

    def get_posts_missing_features(self):
        session = self.DBSession()
        res = session.query(Post).filter((Post.type == PostType.IMAGE) & (Post.status == PostStatus.NOT_INDEXED))
        session.close()
        return res

    def post_count(self):
        session = self.DBSession()
        res = session.query(func.count(Post.id)).filter(Post.type == PostType.IMAGE).scalar()
        session.close()
        return res

    def get_post_by_id(self, id):
        session = self.DBSession()
        res = session.query(Post).filter_by(id=id).scalar()
        session.close()
        return res

    def close(self):
        log.debug("closing database connection {}", self.engine)
        self.engine.dispose()
        log.debug("closed database connection {}", self.engine)
