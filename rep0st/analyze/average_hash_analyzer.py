import cv2
import numpy
from injector import Binder, Module, multiprovider, singleton

from rep0st.analyze import Analyzer, Analyzers, InputImage

TYPE_NAME = "AHASH"


@singleton
class AverageHashAnalyzer(Analyzer):
  hash_size: int = None

  def __init__(self, hash_size: int = 8) -> None:
    self.hash_size = hash_size

  def get_type(self) -> str:
    return TYPE_NAME

  def analyze(self, input_image: InputImage) -> numpy.ndarray:
    image = input_image.gray
    scaled = cv2.resize(
        image, (self.hash_size, self.hash_size), interpolation=cv2.INTER_AREA)
    pixels = scaled.reshape((-1, 1))
    avg = pixels.mean()
    diff = pixels > avg
    return numpy.packbits(numpy.uint8(diff))


class AverageHashAnalyzerModule(Module):

  def configure(self, binder: Binder) -> None:
    binder.bind(AverageHashAnalyzer)

  @multiprovider
  def provide_analyzers(
      self, average_hash_analyzer: AverageHashAnalyzer) -> Analyzers:
    return [average_hash_analyzer]
