import cv2
import numpy
from injector import Binder, Module, multiprovider, singleton

from rep0st.analyze import Analyzer, Analyzers, InputImage

TYPE_NAME = "FEATURE_VECTOR"


@singleton
class FeatureVectorAnalyzer(Analyzer):

  def get_type(self) -> str:
    return TYPE_NAME

  def analyze(self, input_image: InputImage) -> numpy.ndarray:
    image = input_image.bgr

    scaled = cv2.resize(image, (6, 6), interpolation=cv2.INTER_AREA)
    scaled = cv2.cvtColor(scaled, cv2.COLOR_BGR2HSV)

    # extract image channels
    hue = (scaled[:, :, 0] / 2).astype(numpy.uint8)
    sat = scaled[:, :, 1]
    val = scaled[:, :, 2]

    # concat channels for feature vector
    return numpy.hstack((hue.flat, sat.flat, val.flat))


class FeatureVectorAnalyzerModule(Module):

  def configure(self, binder: Binder) -> None:
    binder.bind(FeatureVectorAnalyzer)

  @multiprovider
  def provide_analyzers(
      self, feature_vector_analyzer: FeatureVectorAnalyzer) -> Analyzers:
    return [feature_vector_analyzer]
