import json
import logging
from typing import Any, List

from absl import flags
import cv2
import numpy
from numpy.typing import NDArray
from injector import Binder, Module, inject, singleton
from joblib import Parallel, delayed, parallel_backend
from sqlalchemy import and_

from rep0st import util
from rep0st.db.post import Post, PostRepository, PostRepositoryModule, Type
from rep0st.framework import app
from rep0st.framework.execute import execute
from rep0st.service.media_service import ReadMediaService, ReadMediaServiceModule

log = logging.getLogger(__name__)
FLAGS = flags.FLAGS
flags.DEFINE_string('rep0st_generate_scaled_output_file', 'scaled_posts.txt',
                    'Path to the file where the scaled images are written to.')


class GenerateScaledJobModule(Module):

  def configure(self, binder: Binder):
    binder.install(PostRepositoryModule)
    binder.install(ReadMediaServiceModule)
    binder.bind(GenerateScaledJob)


class WorkItem:
  id: int = None
  type: Type = None
  image: str = None
  fullsize: str = None
  scaled_uint8: NDArray = None
  scaled_float32: NDArray = None

  def __init__(self, post: Post):
    self.id = post.id
    self.type = post.type
    self.image = post.image
    self.fullsize = post.fullsize

  def toJSON(self):
    return {
        'id': self.id,
        'image': self.image,
        'fullsize': self.fullsize,
        'scaled_uint8': self.scaled_uint8.tolist(),
        'scaled_float32': self.scaled_float32.tolist(),
    }


@singleton
class GenerateScaledJob:
  post_repository: PostRepository
  read_media_service: ReadMediaService

  @inject
  def __init__(self, post_repository: PostRepository,
               read_media_service: ReadMediaService):
    self.post_repository = post_repository
    self.read_media_service = read_media_service

  def _process(self, work_post: WorkItem) -> WorkItem:
    try:
      image = next(self.read_media_service.get_images(work_post))
      work_post.scaled_uint8 = cv2.resize(
          image, (6, 6), interpolation=cv2.INTER_AREA)
      image = image.astype(numpy.float32)
      work_post.scaled_float32 = cv2.resize(
          image, (6, 6), interpolation=cv2.INTER_AREA)
    except:
      log.exception(f'Error processing post {work_post.id}')

  @execute()
  def generate_scaled(self):
    with open(FLAGS.rep0st_generate_scaled_output_file,
              'w') as scaled_posts_file:
      with parallel_backend('threading'), Parallel() as parallel:
        max_id = self.post_repository.get_latest_post_id()
        for batch_start, batch_end in util.batched_ranges(1, max_id, 10000):
          posts = self.post_repository.get_posts(type=Type.IMAGE).filter(
              and_(Post.error_status == None, Post.deleted == False, Post.id
                   >= batch_start, Post.id <= batch_end))
          log.info(f'Scaling posts {batch_start}-{batch_end}')

          work_posts = [WorkItem(post) for post in posts]

          parallel(
              delayed(self._process)(work_post) for work_post in work_posts)

          for work_post in work_posts:
            if work_post.scaled_uint8 is not None and work_post.scaled_float32 is not None:
              scaled_posts_file.write(json.dumps(work_post.toJSON()))
              scaled_posts_file.write('\n')


def modules() -> List[Any]:
  return [GenerateScaledJobModule]


if __name__ == "__main__":
  app.run(modules)
