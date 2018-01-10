import os

import cv2
import numpy
import requests
from flask import Flask
from flask import render_template
from flask import request

import config

import sys

from mobiledetect import detect

app = Flask(__name__, template_folder='templates', static_folder='static')

rep = config.get_rep0st()
if config.IS_PRODUCTION:
    rep.get_index()


@app.route("/", methods=["GET"])
def starting_page():
    return custom_render_template()


@app.route("/", methods=["POST"])
def search():
    url = request.form.get("url")
    image = request.files.get("image")

    search_results = None
    error = None
    curr_image = None

    if url != "" and image.filename != "":
        error = "Man kann nicht ein Bild und eine URL angeben!"
    else:
        try:
            if url != "":
                if check_url(url):
                    curr_image = get_image_from_url(url)
                else:
                    error = "Ungueltige URL!"
            elif fileValid(image):
                curr_image = numpy.fromstring(image.read(), numpy.uint8)
            else:
                error = "Keine URL oder Bild angegeben!"
        except Exception as ex:
            error = "Ein unbekannter Fehler " + str(ex)

        if error is None and curr_image is not None:
            if check_image(curr_image):
                curr_image = cv2.imdecode(curr_image, cv2.IMREAD_COLOR)
                search_results = rep.get_index().search(curr_image)

                nsfl = "nsfl" in request.form.getlist("filter")
                nsfw = "nsfw" in request.form.getlist("filter")
                sfw = "sfw" in request.form.getlist("filter")
                
                if not nsfl:
                    while True:
                        nsfl_c = 0
                        for u in search_results:
                            if u.post.is_nsfl():
                                nsfl_c = nsfl_c + 1
                        if nsfl_c == 0:
                            break
                        else:
                            for u in search_results:
                                if u.post.is_nsfl():
                                    search_results.remove(u)

                if not nsfw:
                    while True:
                        nsfw_c = 0
                        for u in search_results:
                            if u.post.is_nsfw():
                                nsfw_c = nsfw_c + 1
                        if nsfw_c == 0:
                            break
                        else:
                            for u in search_results:
                                if u.post.is_nsfw():
                                    search_results.remove(u)

                if not sfw:
                    while True:
                        sfw_c = 0
                        for u in search_results:
                            if u.post.is_sfw():
                                sfw_c = sfw_c + 1
                        if sfw_c == 0:
                            break
                        else:
                            for u in search_results:
                                if u.post.is_sfw():
                                    search_results.remove(u)

            else:
                error = "Ungueltiges Bild"

    return custom_render_template(error=error, search_results=search_results)


def check_url(url):
    try:
        requests.get(url)
    except:
        return False
    return True


def get_image_from_url(url):
    resp = requests.get(url)
    resp.raise_for_status()
    content = resp.content
    return numpy.asarray(bytearray(content), dtype=numpy.uint8)


def check_image(imagedata):
    try:
        image = cv2.imdecode(imagedata, cv2.IMREAD_COLOR)
        if (type(image) != numpy.ndarray):
            return False
        return True
    except Exception as ex:
        return False


def fileValid(ifile):
    ifile.seek(0, os.SEEK_END)
    if ifile == '' or ifile.tell() == 0:
        return False
    ifile.seek(0)
    return True


def custom_render_template(error=None, search_results=None):
    template = "index.html"
    if detect.MobileDetect(useragent=request.headers.get('User-Agent')).is_mobile():
       template = "mobile.html"
    
    return render_template(template, error=error, search_results=search_results, stats=rep.get_statistics())


if __name__ == "__main__":
    app.run(host="0.0.0.0")
