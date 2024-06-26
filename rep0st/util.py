from itertools import islice
import logging
from typing import Callable, Iterable, Iterator, List, TypeVar

import numpy

log = logging.getLogger(__name__)

T = TypeVar('T')
_UNSET = object()


def batch(n: int, i: Iterator[T]) -> Iterable[List[T]]:
  piece = list(islice(i, n))
  while piece:
    yield piece
    piece = list(islice(i, n))


def batched_ranges(start, end, batch_size):
  for i in range(start, end, batch_size):
    yield (i, min(i + batch_size - 1, end))


def AutoJSONEncoder(obj):
  if hasattr(obj, '__json__'):
    return obj.__json__()
  elif isinstance(obj, numpy.float32):
    return float(obj)
  raise TypeError("{} of type {} is not JSON serializable".format(
      obj, type(obj)))


def iterator_every(it: Iterable[T], every: int = 100, msg=str):
  counter = 0
  for e in it:
    yield e
    counter += 1
    if counter % every == 0:
      log.debug(msg.format(current=counter))


def get_secret(content, file_flag):
  if file_flag:
    with open(file_flag, 'r') as file:
      content = file.read().strip()
  return content
