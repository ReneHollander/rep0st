import os

import cv2
import numpy
import redis
import requests
import config
from flask import Flask
from flask import render_template
from flask import request
from sqlalchemy import create_engine

from rep0st import rep0st

app = Flask(__name__)

# rep = rep0st(
#     create_engine('mysql+cymysql://rep0st:rep0stpw@localhost/rep0st?charset=utf8'),
#     redis.StrictRedis(host='localhost', port=6379, db=0),
#     "/media/pr0gramm/images")
rep = config.create_rep0st()

@app.route("/", methods=["GET"])
def starting_page():
    return custom_render_template()


@app.route("/", methods=["POST"])
def search():
    url = request.form.get("url")
    image = request.files.get("image")

    if url != "" and image.filename != "":
        return custom_render_template(error="Man kann nicht ein Bild und eine URL angeben!")
    else:
        try:
            if url != "":
                return check_url(url)
            elif fileValid(image):
                return check_image(numpy.fromstring(image.read(), numpy.uint8))
            else:
                return custom_render_template(error="Keine URL oder Bild angegeben!")
        except Exception as ex:
            custom_render_template(error="Ein unbekannter Fehler " + str(ex))


def check_url(url):
    try:
        resp = requests.get(url)
    except:
        return custom_render_template(error="Ungueltige URL!")

    resp.raise_for_status()
    content = resp.content
    return check_image(numpy.asarray(bytearray(content), dtype=numpy.uint8))


def check_image(imagedata):
    try:
        image = cv2.imdecode(imagedata, cv2.IMREAD_COLOR)
        if (type(image) != numpy.ndarray):
            return custom_render_template(error="Ungueltiges Bild!")

        images = rep.get_index().search(image)
        posts = [images[a].post for a in range(len(images))]
        return custom_render_template(images=posts)
    except Exception as ex:
        return custom_render_template(error="Unbekannter Fehler: " + str(ex))


def fileValid(ifile):
    ifile.seek(0, os.SEEK_END)
    if ifile == '' or ifile.tell() == 0:
        return False
    ifile.seek(0)
    return True

def custom_render_template(error = None, images = None):
    return render_template("index.html", error=error, images=images, stats=rep.get_statistics())


if __name__ == "__main__":
    app.run(host="0.0.0.0")
