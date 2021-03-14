import cv2
import numpy
import pywt
from injector import Module, multiprovider, singleton

from rep0st.analyze import Analyzer, Analyzers, InputImage

TYPE_NAME = "WHASH"


@singleton
class WaveletHashAnalyzer(Analyzer):
  hash_size: int = None
  image_scale: int = None
  mode: str = None
  remove_max_haar_ll: bool = None

  def __init__(self,
               hash_size: int = 8,
               image_scale: int = None,
               mode: str = 'haar',
               remove_max_haar_ll: bool = True) -> None:
    self.hash_size = hash_size
    self.image_scale = image_scale
    self.mode = mode
    self.remove_max_haar_ll = remove_max_haar_ll

  def get_type(self) -> str:
    return TYPE_NAME

  def analyze(self, input_image: InputImage) -> numpy.ndarray:
    image = input_image.gray

    if self.image_scale is not None:
      assert self.image_scale & (self.image_scale -
                                 1) == 0, "image_scale is not power of 2"
    else:
      image_natural_scale = 2**int(numpy.log2(min(image.shape[0:2])))
      image_scale = max(image_natural_scale, self.hash_size)

    ll_max_level = int(numpy.log2(image_scale))

    level = int(numpy.log2(self.hash_size))
    assert self.hash_size & (self.hash_size -
                             1) == 0, "hash_size is not power of 2"
    assert level <= ll_max_level, "hash_size in a wrong range"
    dwt_level = ll_max_level - level

    scaled = cv2.resize(
        image, (image_scale, image_scale), interpolation=cv2.INTER_AREA)
    pixels = numpy.float32(scaled)
    pixels /= 255

    # Remove low level frequency LL(max_ll) if @remove_max_haar_ll using haar filter
    if self.remove_max_haar_ll:
      coeffs = pywt.wavedec2(pixels, 'haar', level=ll_max_level)
      coeffs = list(coeffs)
      coeffs[0] *= 0
      pixels = pywt.waverec2(coeffs, 'haar')

    # Use LL(K) as freq, where K is log2(@hash_size)
    coeffs = pywt.wavedec2(pixels, self.mode, level=dwt_level)
    dwt_low = coeffs[0]

    # Substract median and compute hash
    med = numpy.median(dwt_low)
    diff = dwt_low > med
    return numpy.packbits(numpy.uint8(diff.reshape(-1, 1)))


class WaveletHashAnalyzerModule(Module):

  def configure(self, binder):
    binder.bind(WaveletHashAnalyzer)

  @multiprovider
  def provide_analyzers(
      self, wavelet_hash_analyzer: WaveletHashAnalyzer) -> Analyzers:
    return [wavelet_hash_analyzer]
