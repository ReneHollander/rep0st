from typing import List

from injector import Binder, Module, multiprovider, singleton
from prometheus_client import make_wsgi_app

from rep0st.framework.web import MountPoint, WebApp, WebServerModule


@singleton
class MetriczPage(WebApp):

  def get_mounts(self) -> List[MountPoint]:
    return [MountPoint('/metricz', make_wsgi_app())]


class MetriczPageModule(Module):

  def configure(self, binder: Binder) -> None:
    binder.install(WebServerModule)
    binder.bind(MetriczPage)

  @multiprovider
  def provide_metricz_page(self, metricz_page: MetriczPage) -> List[WebApp]:
    return [metricz_page]
