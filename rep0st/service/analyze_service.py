import logging
import time
from typing import Dict, List

import cv2
import numpy
from injector import Module, inject, singleton

from rep0st.analyze import Analyzer, Analyzers, InputImage
from rep0st.analyze.feature_vector_analyzer import FeatureVectorAnalyzerModule

log = logging.getLogger(__name__)


class AnalyzeServiceModule(Module):

  def configure(self, binder):
    binder.install(FeatureVectorAnalyzerModule)
    # TODO(rhollander): Enable other analyzers.
    # binder.install(AverageHashAnalyzerModule)
    # binder.install(DifferenceHashAnalyzerModule)
    # binder.install(PerceptualHashAnalyzerModule)
    # binder.install(WaveletHashAnalyzerModule)
    binder.bind(AnalyzeService)


@singleton
class AnalyzeService:
  _analyzers: List[Analyzer] = None

  @inject
  def __init__(self, analyzers: Analyzers) -> None:
    self._analyzers = set(analyzers)
    for analyzer in self._analyzers:
      log.info(f'Registered analyzer {analyzer.get_type()}')

  def analyze(self, image: numpy.ndarray):
    input_image = InputImage(image, cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))

    result = {}
    for analyzer in self._analyzers:
      start = time.time()
      result[analyzer.get_type()] = analyzer.analyze(input_image)
      end = time.time()
      time_taken = end - start
      log.debug(
          f'Analyzed image {image.shape} with analyzer {analyzer.get_type()} in {time_taken * 1000:.2f}ms'
      )
    return result
