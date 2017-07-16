from abc import abstractmethod, ABC
from collections import namedtuple

import cv2
import numpy
import pywt

from database import FeatureType


class Analyzer(ABC):
    @abstractmethod
    def get_type(self):
        pass

    @abstractmethod
    def analyze(self, images):
        pass


class FeatureVectorAnalyzer(Analyzer):
    def get_type(self):
        return FeatureType.FEATURE_VECTOR

    def analyze(self, images):
        image = images['bgr']

        scaled = cv2.resize(image, (6, 6), interpolation=cv2.INTER_AREA)
        scaled = cv2.cvtColor(scaled, cv2.COLOR_BGR2HSV)

        # extract image channels
        hue = (scaled[:, :, 0] / 2).astype(numpy.uint8)
        sat = scaled[:, :, 1]
        val = scaled[:, :, 2]

        # concat channels for feature vector
        return numpy.hstack((hue.flat, sat.flat, val.flat))

        # scaled = cv2.resize(image, (6, 6), interpolation=cv2.INTER_AREA)
        # scaled = cv2.cvtColor(scaled, cv2.COLOR_BGR2HSV)
        #
        # # extract image channels
        # hue_sin = (numpy.sin(scaled[:, :, 0] / (255.0 / (2 * numpy.math.pi))) * 128 + 128).astype(numpy.uint8)
        # hue_cos = (numpy.cos(scaled[:, :, 0] / (255.0 / (2 * numpy.math.pi))) * 128 + 128).astype(numpy.uint8)
        # sat = scaled[:, :, 1]
        # val = scaled[:, :, 2]
        #
        # # concat channels for feature vector
        # return numpy.hstack((hue_sin.flat, hue_cos.flat, sat.flat, val.flat))


class AverageHashAnalyzer(Analyzer):
    def __init__(self, hash_size=8):
        self.hash_size = hash_size

    def get_type(self):
        return FeatureType.AHASH

    def analyze(self, images):
        image = images['gray']
        scaled = cv2.resize(image, (self.hash_size, self.hash_size), interpolation=cv2.INTER_AREA)
        pixels = scaled.reshape((-1, 1))
        avg = pixels.mean()
        diff = pixels > avg
        return numpy.packbits(numpy.uint8(diff))


class PerceptualHashAnalyzer(Analyzer):
    def __init__(self, hash_size=8, highfreq_factor=4):
        self.hash_size = hash_size
        self.highfreq_factor = highfreq_factor
        self.img_size = self.hash_size * self.highfreq_factor

    def get_type(self):
        return FeatureType.PHASH

    def analyze(self, images):
        image = images['gray']
        scaled = cv2.resize(image, (self.img_size, self.img_size), interpolation=cv2.INTER_AREA)
        scaled = numpy.float32(scaled)
        dct = cv2.dct(scaled)
        dctlowfreq = dct[:self.hash_size, :self.hash_size]
        med = numpy.median(dctlowfreq)
        diff = dctlowfreq > med
        return numpy.packbits(numpy.uint8(diff.reshape(-1, 1)))


class DifferenceHashAnalyzer(Analyzer):
    def __init__(self, hash_size=8):
        self.hash_size = hash_size

    def get_type(self):
        return FeatureType.DHASH

    def analyze(self, images):
        image = images['gray']
        scaled = cv2.resize(image, (self.hash_size + 1, self.hash_size), interpolation=cv2.INTER_AREA)
        pixels = numpy.float32(scaled).reshape((self.hash_size, self.hash_size + 1))
        # compute differences between columns
        diff = pixels[:, 1:] > pixels[:, :-1]
        return numpy.packbits(numpy.uint8(diff.reshape(-1, 1)))


class WaveletHashAnalyzer(Analyzer):
    def __init__(self, hash_size=8, image_scale=None, mode='haar', remove_max_haar_ll=True):
        self.hash_size = hash_size
        self.image_scale = image_scale
        self.mode = mode
        self.remove_max_haar_ll = remove_max_haar_ll

    def get_type(self):
        return FeatureType.WHASH

    def analyze(self, images):
        image = images['gray']

        if self.image_scale is not None:
            assert self.image_scale & (self.image_scale - 1) == 0, "image_scale is not power of 2"
        else:
            image_natural_scale = 2 ** int(numpy.log2(min(image.shape[0:2])))
            image_scale = max(image_natural_scale, self.hash_size)

        ll_max_level = int(numpy.log2(image_scale))

        level = int(numpy.log2(self.hash_size))
        assert self.hash_size & (self.hash_size - 1) == 0, "hash_size is not power of 2"
        assert level <= ll_max_level, "hash_size in a wrong range"
        dwt_level = ll_max_level - level

        scaled = cv2.resize(image, (image_scale, image_scale), interpolation=cv2.INTER_AREA)
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


analyzers = {
    FeatureType.FEATURE_VECTOR: FeatureVectorAnalyzer(),
    FeatureType.AHASH: AverageHashAnalyzer(),
    FeatureType.PHASH: PerceptualHashAnalyzer(),
    FeatureType.DHASH: DifferenceHashAnalyzer(),
    FeatureType.WHASH: WaveletHashAnalyzer()
}

AnalyzeResult = namedtuple('AnalyzeResult', 'type, data')


def analyze_image(image):
    images = {
        'bgr': image,
        'gray': cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    }

    result = {}
    for type, analyzer in analyzers.items():
        result[analyzer.get_type()] = analyzer.analyze(images)
    return result
