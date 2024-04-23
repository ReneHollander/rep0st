import logging
import os
from pathlib import Path
from injector import Binder, Module, inject, singleton
from prometheus_client import Counter

from rep0st.db.post import Post, Status, Type
from rep0st.pr0gramm.api import APIException, Pr0grammAPI, Pr0grammAPIModule
from rep0st.service.media_service import _MediaDirectory, _MediaFlagModule

log = logging.getLogger(__name__)

download_media_service_renamed_count_z = Counter(
    'download_media_service_renamed_count',
    'Number of successfully renamed media files')
download_media_service_rename_errors_count_z = Counter(
    'download_media_service_rename_errors_count',
    'Number of errors encountered while performing media rename operations')


class DownloadMediaServiceModule(Module):

  def configure(self, binder: Binder):
    binder.install(Pr0grammAPIModule)
    binder.install(_MediaFlagModule)
    binder.bind(DownloadMediaService)


class DownloadMediaException(Exception):
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
      if media_file.is_file() and post.status != Status.MEDIA_BROKEN:
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
      except (IOError, OSError) as e:
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

  def rename_media(self, old_post: Post, new_post: Post) -> Post:
    if old_post.id != new_post.id:
      raise ValueError(f'Posts have to have matching IDs')

    def _do(old_media, new_media, dir_prefix=''):
      if old_media == new_media:
        log.debug(f'Media {old_media} already has the correct name')
        return False
      try:
        old_file = self.media_dir / dir_prefix / old_media
        new_file = self.media_dir / dir_prefix / new_media
        log.debug(
            f'Renaming files for post {old_post.id}: {old_file} -> {new_file}')
        os.renames(old_file, new_file)
        download_media_service_renamed_count_z.inc()
        return True
      except Exception:
        log.exception(
            f'Error moving media {old_media} to {new_media} for post {old_post.id} {old_post.status}'
        )
        download_media_service_rename_errors_count_z.inc()

    if old_post.fullsize:
      if _do(old_post.fullsize, new_post.fullsize, dir_prefix='full'):
        old_post.fullsize = new_post.fullsize

    if _do(old_post.image, new_post.image):
      old_post.image = new_post.image

    return old_post
