from typing import Any, List
from pathlib import Path
from absl import flags
from rep0st.framework import app
from rep0st.framework.web import WebServerModule
from rep0st.web.site import SiteModule
from rep0st.web.api import ApiModule
from rep0st.web.static import StaticFilesModule
from rep0st.web.templates import TemplateModule


def modules() -> List[Any]:
  return [
      WebServerModule, TemplateModule, StaticFilesModule, ApiModule, SiteModule
  ]


if __name__ == "__main__":
  app.run(modules)
