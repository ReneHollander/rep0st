import logging
from pathlib import Path
from injector import Binder, Module, inject, singleton

from rep0st.db.post import Post, Type
from rep0st.pr0gramm.api import APIException, Pr0grammAPI, Pr0grammAPIModule
from rep0st.service.media_service import _MediaDirectory, _MediaFlagModule

log = logging.getLogger(__name__)


class DownloadMediaServiceModule(Module):

  def configure(self, binder: Binder):
    binder.install(Pr0grammAPIModule)
    binder.install(_MediaFlagModule)
    binder.bind(DownloadMediaService)


class DownloadMediaException(BaseException):
  pass


@singleton
class DownloadMediaService:
  api: Pr0grammAPI
  media_dir: Path

  @inject
  def __init__(self, api: Pr0grammAPI, media_dir: _MediaDirectory):
    self.api = api
    self.media_dir = media_dir

  def download_media(self, post: Post):

    def _download_media(path: str, dl_fn, dir_prefix: str = ''):
      media_file = self.media_dir / dir_prefix / path
      if media_file.is_file():
        log.debug(
            f'Media for post {post.id} found at location {media_file.absolute()}, skipping download'
        )
        return
      log.debug(f'Downloading media for post {post.id}')
      try:
        data = dl_fn(path)
      except APIException as e:
        raise DownloadMediaException(
            f'Could not download media for post {post.id}') from e
      try:
        media_file.parent.mkdir(parents=True, exist_ok=True)
        with media_file.open('wb') as f:
          f.write(data)
        return
      except IOError or OSError as e:
        raise DownloadMediaException(
            f'Could not save media for post {post.id} to file {media_file.absolute()}'
        ) from e

    if post.fullsize:
      try:
        _download_media(
            post.fullsize, self.api.download_fullsize, dir_prefix='full')
      except:
        log.exception('Error downloading fullsize image. Skipping...')

    if post.type == Type.IMAGE or post.type == Type.ANIMATED:
      _download_media(post.image, self.api.download_image)
    elif post.type == Type.VIDEO:
      _download_media(post.image, self.api.download_video)
    else:
      log.error(
          f'Error downloading media for post {post.id} with unknown type {post.type}'
      )
