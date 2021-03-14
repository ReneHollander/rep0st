import logging
from pathlib import Path
from typing import List

from injector import Binder, Module, multiprovider, singleton
from werkzeug.exceptions import NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware

from rep0st.framework.web import MountPoint, WebApp

log = logging.getLogger(__name__)


@singleton
class StaticFiles(WebApp):

  def __init__(self):
    self.app = SharedDataMiddleware(
        NotFound, {'/': str(Path(__file__).parent.absolute())})

  def get_mounts(self) -> List[MountPoint]:
    return [MountPoint('/static', self.app)]


class StaticFilesModule(Module):

  def configure(self, binder: Binder) -> None:
    binder.bind(StaticFiles)

  @multiprovider
  def provide_static_files(self, static_files: StaticFiles) -> List[WebApp]:
    return [static_files]
