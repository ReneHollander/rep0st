from abc import ABC, abstractmethod
from typing import List, NamedTuple

import numpy


class InputImage(NamedTuple):
  bgr: numpy.ndarray
  gray: numpy.ndarray


class Analyzer(ABC):

  @abstractmethod
  def get_type(self) -> str:
    pass

  @abstractmethod
  def analyze(self, image: InputImage) -> numpy.ndarray:
    pass


Analyzers = List[Analyzer]
