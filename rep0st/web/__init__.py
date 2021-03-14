import logging
from typing import BinaryIO, Optional

import requests
from werkzeug import Request

log = logging.getLogger(__name__)


class MediaHelper:

  def file_from_url(self, url: str) -> Optional[bytes]:
    try:
      resp = requests.get(url)
      resp.raise_for_status()
      return resp.content
    except:
      log.exception('error getting file from url {url}')
      return None

  def file_from_post_request(self, req: Request) -> Optional[BinaryIO]:
    if 'image' not in req.files:
      return None

    image_file = req.files['image']
    if image_file.filename == '':
      return None

    return image_file
