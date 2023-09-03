import logging
from pathlib import Path
from typing import BinaryIO, Callable, Dict, Iterable, NewType, Union, IO
import numpy
from absl import flags
from cv2 import IMREAD_COLOR, imdecode, cvtColor, COLOR_RGB2BGR
from injector import Binder, Module, inject, singleton
import ffmpeg
import subprocess

from rep0st.db.post import Post, Type

log = logging.getLogger(__name__)
FLAGS = flags.FLAGS
flags.DEFINE_string('rep0st_media_path', '',
                    'Path to media directory used by rep0st to save media.')
_MediaDirectory = NewType('_MediaDirectory', Path)


def _readline(stream: IO[bytes]) -> Union[None, str]:
  out_bytes = bytes()
  c = stream.read(1)
  if not c:
    return None
  while c != b'\n':
    out_bytes += c
    c = stream.read(1)
  return out_bytes.decode('ascii').strip()


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

  def decode_video_from_file(self, file: BinaryIO) -> Iterable[numpy.ndarray]:
    cmd = ffmpeg.input(
        'pipe:',
        vsync=0,
        skip_frame='nokey',
        hide_banner=None,
        threads=1,
        loglevel='error').output(
            'pipe:', vcodec='ppm', format='rawvideo')
    proc = subprocess.Popen(
        cmd.compile(),
        stdin=file,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    while True:
      format = _readline(proc.stdout)
      if not format:
        break
      if format != 'P6':
        raise ImageDecodeException(
            'frames returned by ffmpeg cannot be decoded due to an unsupported format'
        )
      width, height = [int(x) for x in _readline(proc.stdout).split(' ')]
      max_value = int(_readline(proc.stdout))
      if max_value != 255:
        raise ImageDecodeException(
            f'max_value has to be 255, it is {max_value}')

      in_bytes = proc.stdout.read(width * height * 3)
      if not in_bytes:
        raise ImageDecodeException('could not read the full frame')
      in_frame = numpy.frombuffer(in_bytes,
                                  numpy.uint8).reshape([height, width, 3])
      in_frame = cvtColor(in_frame, COLOR_RGB2BGR)
      yield in_frame

    retcode = proc.wait(timeout=1)

    if retcode != 0:
      err = proc.stderr.read().decode('utf-8')
      raise ImageDecodeException(err)


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
  decoders: Dict[Type, Callable[[Iterable[numpy.ndarray]], BinaryIO]]

  @inject
  def __init__(self, media_dir: _MediaDirectory,
               decode_media_service: DecodeMediaService):
    self.media_dir = media_dir
    self.decode_media_service = decode_media_service
    self.decoders = {
        Type.IMAGE: self.decode_media_service.decode_image_from_file,
        Type.VIDEO: self.decode_media_service.decode_video_from_file,
    }

  def get_images(self, post: Post) -> Iterable[numpy.ndarray]:
    media_file = self.media_dir / post.image

    if post.fullsize:
      fullsize_media_file = self.media_dir / 'full' / post.fullsize
      if not fullsize_media_file.is_file():
        log.error(
            f'Fullsize image for {post.id} not found at {fullsize_media_file.absolute()}. Falling back to resized image'
        )
      else:
        log.debug(f'Using fullsize image {fullsize_media_file.absolute()}')
        media_file = fullsize_media_file

    if post.type not in self.decoders:
      raise NotImplementedError(
          f'Decoder needed for {post} for type {post.type} is not implemented')

    try:
      with media_file.open("rb") as f:
        for image in self.decoders[post.type](f):
          yield image
    except (IOError, OSError) as e:
      raise NoMediaFoundException(
          f'Could not read images for post {post.id} from file {media_file.absolute()}'
      ) from e
