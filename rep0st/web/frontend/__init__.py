from pathlib import Path

from injector import Module

from rep0st.framework.webpack import WebpackModule
from rep0st.web.frontend.main import MainModule


class FrontendModule(Module):

  def configure(self, binder):
    binder.install(
        WebpackModule(webpack_output_path=Path(__file__).parent / 'static'))
    binder.install(MainModule)
