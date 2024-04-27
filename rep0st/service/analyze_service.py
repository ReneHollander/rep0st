import logging
import time

import cv2
import numpy
from numpy.typing import NDArray
from injector import Module, singleton

log = logging.getLogger(__name__)


class AnalyzeServiceModule(Module):

  def configure(self, binder):
    binder.bind(AnalyzeService)


def _calculate_feature_vec(image: NDArray) -> NDArray:
  image = image.astype(numpy.float32)
  scaled = cv2.resize(image, (6, 6), interpolation=cv2.INTER_AREA)
  # cvtColor expects floating point image to be normalized between 0 and 1
  scaled *= (1. / 255.)
  hsv = cv2.cvtColor(scaled, cv2.COLOR_BGR2HSV)

  # extract image channels
  # 0<=H<=360
  hue = hsv[:, :, 0]
  # Divide by:
  #   2 to get the 0<=H<=360 value into 0.255
  #   2 again for magic reasons
  #   255 to normalize between 0 and 1
  hue *= (1. / 2. / 2. / 255.)

  # 0<=S<=1
  sat = hsv[:, :, 1]
  # 0<=S<=1
  val = hsv[:, :, 2]

  # concat channels for feature vector
  vec = numpy.concatenate((hue.flatten(), sat.flatten(), val.flatten()))

  return vec


@singleton
class AnalyzeService:

  def analyze(self, image: NDArray) -> NDArray[numpy.float32]:
    start = time.time()
    vec = _calculate_feature_vec(image)
    end = time.time()
    time_taken = end - start
    log.debug(f'Analyzed image in {time_taken * 1000:.2f}ms')
    return vec
