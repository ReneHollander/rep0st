import logging
from pathlib import Path
from typing import BinaryIO, Iterable, NewType

import numpy
from absl import flags
from cv2.cv2 import IMREAD_COLOR, imdecode
from injector import Binder, Module, inject, singleton

from rep0st.db.post import Post, Type

log = logging.getLogger(__name__)
FLAGS = flags.FLAGS
flags.DEFINE_string('rep0st_media_path', '',
                    'Path to media directory used by rep0st to save media.')
_MediaDirectory = NewType('_MediaDirectory', Path)


class _MediaFlagModule(Module):

  def configure(self, binder: Binder) -> None:
    media_path = Path(FLAGS.rep0st_media_path)
    if FLAGS.rep0st_media_path == '' or not media_path.is_dir():
      raise NotADirectoryError(
          'rep0st_media_path has to be set to an existing directory.')
    binder.bind(_MediaDirectory, to=media_path)


class DecodeMediaServiceModule(Module):

  def configure(self, binder: Binder):
    binder.bind(DecodeMediaService)


@singleton
class DecodeMediaService:

  def _decode_image(self, data: numpy.ndarray) -> numpy.ndarray:
    try:
      img = imdecode(data, IMREAD_COLOR)
      if img is None:
        raise ImageDecodeException("Could not decode image")
      return img
    except:
      raise ImageDecodeException("Could not decode image")

  def decode_image_from_buffer(self, data: bytes) -> Iterable[numpy.ndarray]:
    try:
      data = numpy.frombuffer(data, dtype=numpy.uint8)
    except (IOError, OSError) as e:
      raise NoMediaFoundException('Could not data from buffer') from e
    yield self._decode_image(data)

  def decode_image_from_file(self, file: BinaryIO) -> Iterable[numpy.ndarray]:
    try:
      data = numpy.fromfile(file, dtype=numpy.uint8)
    except (IOError, OSError) as e:
      raise NoMediaFoundException(
          f'Could not read data from file {file}') from e
    yield self._decode_image(data)


class ReadMediaServiceModule(Module):

  def configure(self, binder: Binder):
    binder.install(DecodeMediaServiceModule)
    binder.install(_MediaFlagModule)
    binder.bind(ReadMediaService)


class NoMediaFoundException(Exception):
  pass


class ImageDecodeException(Exception):
  pass


@singleton
class ReadMediaService:
  media_dir: Path
  decode_media_service: DecodeMediaService

  @inject
  def __init__(self, media_dir: _MediaDirectory,
               decode_media_service: DecodeMediaService):
    self.media_dir = media_dir
    self.decode_media_service = decode_media_service

  def get_images(self, post: Post) -> Iterable[numpy.ndarray]:
    if post.type != Type.IMAGE:
      # TODO(rhollander): Allow extration of images in gifs and videos.
      yield

    media_file = self.media_dir / post.image

    if post.fullsize:
      fullsize_media_file = self.media_dir / 'full' / post.fullsize
      if not fullsize_media_file.is_file():
        log.error(
            f'Fullsize image for {post.id} not found at {fullsize_media_file.absolute()}. Falling back to resized image'
        )
      else:
        log.info(f'using fullsize image {fullsize_media_file.absolute()}')
        media_file = fullsize_media_file

    try:
      with media_file.open("rb") as f:
        for image in self.decode_media_service.decode_image_from_file(f):
          yield image
    except (IOError, OSError) as e:
      raise NoMediaFoundException(
          f'Could not read image for post {post.id} from file {media_file.absolute()}'
      ) from e
