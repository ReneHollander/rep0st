import cv2
import numpy
from injector import Binder, Module, multiprovider, singleton

from rep0st.analyze import Analyzer, Analyzers, InputImage

TYPE_NAME = "PHASH"


@singleton
class PerceptualHashAnalyzer(Analyzer):
  hash_size: int = None
  highfreq_factor: int = None
  img_size: int = None

  def __init__(self, hash_size: int = 8, highfreq_factor: int = 4) -> None:
    self.hash_size = hash_size
    self.highfreq_factor = highfreq_factor
    self.img_size = self.hash_size * self.highfreq_factor

  def get_type(self) -> str:
    return TYPE_NAME

  def analyze(self, input_image: InputImage) -> numpy.ndarray:
    image = input_image.gray
    scaled = cv2.resize(
        image, (self.img_size, self.img_size), interpolation=cv2.INTER_AREA)
    scaled = numpy.float32(scaled)
    dct = cv2.dct(scaled)
    dctlowfreq = dct[:self.hash_size, :self.hash_size]
    med = numpy.median(dctlowfreq)
    diff = dctlowfreq > med
    return numpy.packbits(numpy.uint8(diff.reshape(-1, 1)))


class PerceptualHashAnalyzerModule(Module):

  def configure(self, binder: Binder) -> None:
    binder.bind(PerceptualHashAnalyzer)

  @multiprovider
  def provide_analyzers(
      self, perceptual_hash_analyzer: PerceptualHashAnalyzer) -> Analyzers:
    return [perceptual_hash_analyzer]
