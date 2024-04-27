import enum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PostType(enum.Enum):
  IMAGE = 'IMAGE'
  ANIMATED = 'ANIMATED'
  VIDEO = 'VIDEO'
  UNKNOWN = 'UNKNOWN'
