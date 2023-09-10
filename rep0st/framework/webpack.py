from dataclasses import dataclass
import json
import logging
import mimetypes
from pathlib import Path
from typing import List, NewType

from injector import Binder, inject, Module, multiprovider, singleton
from werkzeug.utils import get_content_type
from wsgiref.types import WSGIEnvironment, StartResponse

from rep0st.framework import Environment
from rep0st.framework.web import MountPoint, WebApp

log = logging.getLogger(__name__)

_WebpackOutputPathKey = NewType('_WebpackOutputPathKey', Path)
_WebpackMountPathKey = NewType('_WebpackMountPathKey', str)


@dataclass
class ManifestEntry:
  name: str
  path: Path
  served_name: str
  mime_type: str
  size: int


@dataclass
class Manifest:
  name_to_entry: dict[str, ManifestEntry]
  served_name_to_entry: dict[str, ManifestEntry]


@singleton
class Webpack(WebApp):

  env: Environment

  webpack_output_path: Path
  webpack_mount_path: str
  manifest_path: Path

  _cached_manifest: Manifest = None

  @inject
  def __init__(self, env: Environment,
               webpack_output_path: _WebpackOutputPathKey,
               webpack_mount_path: _WebpackMountPathKey):
    self.env = env
    self.webpack_output_path = webpack_output_path
    self.webpack_mount_path = webpack_mount_path

    self.manifest_path = self.webpack_output_path / 'manifest.json'

  def _get_manifest(self) -> Manifest:
    if self.env == Environment.PRODUCTION and self._cached_manifest:
      return self._cached_manifest

    def _create_entry(name: str, path: Path) -> ManifestEntry:
      guessed_type = mimetypes.guess_type(path.name)
      mime_type = get_content_type(
          guessed_type[0] or 'application/octet-stream', 'utf-8')
      return ManifestEntry(
          name=name,
          path=path,
          mime_type=mime_type,
          size=path.stat().st_size,
          served_name=f'/{path.name}')

    with self.manifest_path.open() as manifest_file:
      manifest: dict[str, str] = json.load(manifest_file)

    name_to_entry: dict[str, ManifestEntry] = {}
    served_name_to_entry: dict[str, ManifestEntry] = {}
    for name, relative_path in manifest.items():
      entry = _create_entry(name, self.webpack_output_path / relative_path)
      name_to_entry[entry.name] = entry
      served_name_to_entry[entry.served_name] = entry
    self._cached_manifest = Manifest(
        name_to_entry=name_to_entry,
        served_name_to_entry=served_name_to_entry,
    )
    return self._cached_manifest

  def handler(self, environ: WSGIEnvironment, start_response: StartResponse):
    manifest = self._get_manifest()
    entry = manifest.served_name_to_entry.get(environ['PATH_INFO'], None)
    if not entry:
      start_response('404 Not Found', [])
      return b''

    start_response('200 OK', [
        ('Cache-Control', 'public, max-age=31536000, immutable'
         if self.env == Environment.PRODUCTION else
         'no-store, no-cache, max-age=0, must-revalidate, proxy-revalidate'),
        ('Content-Length', str(entry.size)),
        ('Content-Type', entry.mime_type),
    ])
    return entry.path.open('rb')

  def get_mounts(self) -> List[MountPoint]:
    return [MountPoint(self.webpack_mount_path, self.handler)]

  def __getitem__(self, name):
    return self.webpack_mount_path + self._get_manifest(
    ).name_to_entry[name].served_name


class WebpackModule(Module):

  def __init__(self,
               webpack_output_path: Path,
               webpack_mount_path: str = '/static'):
    self.webpack_output_path = webpack_output_path
    self.webpack_mount_path = webpack_mount_path

  def configure(self, binder: Binder):
    binder.bind(_WebpackOutputPathKey, to=self.webpack_output_path)
    binder.bind(_WebpackMountPathKey, to=self.webpack_mount_path)
    binder.bind(Webpack)

  @multiprovider
  def provide_webpack_app(self, webpack: Webpack) -> List[WebApp]:
    return [webpack]
