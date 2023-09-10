from typing import Any, List

from rep0st.framework import app
from rep0st.framework.web import WebServerModule
from rep0st.web.frontend import FrontendModule
from rep0st.web.api import ApiModule


def modules() -> List[Any]:
  return [WebServerModule, ApiModule, FrontendModule]


if __name__ == "__main__":
  app.run(modules)
