import cv2
import numpy
from injector import Binder, Module, multiprovider, singleton

from rep0st.analyze import Analyzer, Analyzers, InputImage

TYPE_NAME = "DHASH"


@singleton
class DifferenceHashAnalyzer(Analyzer):
  hash_size: int = None

  def __init__(self, hash_size: int = 8) -> None:
    self.hash_size = hash_size

  def get_type(self) -> str:
    return TYPE_NAME

  def analyze(self, input_image: InputImage) -> numpy.ndarray:
    image = input_image.gray
    scaled = cv2.resize(
        image, (self.hash_size + 1, self.hash_size),
        interpolation=cv2.INTER_AREA)
    pixels = numpy.float32(scaled).reshape((self.hash_size, self.hash_size + 1))
    # compute differences between columns
    diff = pixels[:, 1:] > pixels[:, :-1]
    return numpy.packbits(numpy.uint8(diff.reshape(-1, 1)))


class DifferenceHashAnalyzerModule(Module):

  def configure(self, binder: Binder) -> None:
    binder.bind(DifferenceHashAnalyzer)

  @multiprovider
  def provide_analyzers(
      self, difference_hash_analyzer: DifferenceHashAnalyzer) -> Analyzers:
    return [difference_hash_analyzer]
