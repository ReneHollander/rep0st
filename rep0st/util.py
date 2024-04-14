import logging
from itertools import islice
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


def batch_by_index(
    it: Iterator[T],
    start_index: int,
    batch_size: int,
    index_fun: Callable[[T], int],
    default_value: any = _UNSET
) -> Iterable[tuple[int, int, dict[int, T | None]]]:
  batch_start = start_index
  batch_end = batch_size
  batch = {}
  for v in it:
    i = index_fun(v)
    if i > batch_end:
      if default_value != _UNSET:
        for j in range(batch_start, batch_end + 1):
          if not j in batch:
            batch[j] = default_value
      yield batch_start, batch_end, batch
      batch = {}
      batch_start = batch_start + batch_size
      batch_end = batch_end + batch_size
    batch[i] = v


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
