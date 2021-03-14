from typing import Any, List

from injector import Injector


def get_bindings(injector: Injector) -> List[Any]:
  if not injector:
    return []

  return list(injector.binder._bindings.keys()) + get_bindings(injector.parent)
