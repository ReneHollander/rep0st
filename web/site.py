import traceback

import cv2
import numpy
import requests
import simplejson as json
from flask import Flask, request, render_template, Response

import config
from rep0st.rep0st import get_rep0st
from rep0st.util import AutoJSONEncoder

config.load()
app = Flask(__name__, template_folder='templates', static_folder='static')

rep = get_rep0st()
if config.IS_PRODUCTION:
    rep.get_index()


@app.route("/", methods=["GET"])
def starting_page():
    return custom_render_template()


@app.route("/", methods=["POST"])
def search():
    url = request.form.get("url")

    search_results = None
    error = None
    curr_image = None

    if url != "" and 'image' in request.files and request.files['image'].filename != '':
        error = "Man kann nicht ein Bild und eine URL angeben!"
    else:
        try:
            if url != "":
                curr_image = get_image_from_url(url)
                if curr_image is None:
                    error = "Ungueltige URL!"
            elif 'image' in request.files and request.files['image'].filename != '':
                curr_image = numpy.fromstring(request.files['image'].read(), numpy.uint8)
            else:
                error = "Keine URL oder Bild angegeben!"
        except:
            traceback.print_exc()
            error = "Unbekannter Fehler"

        if error is None and curr_image is not None:
            search_results = analyze_image(curr_image)
            if search_results is None:
                error = "Ungueltiges Bild"

    return custom_render_template(error=error, search_results=search_results)


@app.route("/api/search", methods=["POST"])
def api_search_upload():
    if 'image' not in request.files:
        return api_response(error="invalid or no image", status=400)

    image_file = request.files['image']
    if image_file.filename == '':
        return api_response(error="invalid or no image", status=400)

    image = numpy.fromstring(image_file.read(), numpy.uint8)

    results = analyze_image(image)
    if results:
        return api_response(resp=results, status=200)
    else:
        return api_response(error="invalid or no image", status=400)

@app.route("/api/search", methods=["GET"])
def api_search_URL():
    url = request.args.get("url")
    search_results = None
    curr_image = None
    try:
        if not url:
            return api_response(error="url parameter missing", status=400)
        curr_image = get_image_from_url(url)
        if curr_image is None:
            return api_response(error="url is invalid", status=400)
        search_results = analyze_image(curr_image)
        if search_results is None:
            return api_response(error="internal server error", status=500)
        return api_response(resp=search_results, status=200)
    except:
        traceback.print_exc()
        return api_response(error="internal server error", status=500)

def api_response(resp=None, error=None, status=200):
    if error is not None:
        resp = {'error': error}
    return Response(json.dumps(resp, default=AutoJSONEncoder), status=status,
                    mimetype='application/json')


def get_image_from_url(url):
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        content = resp.content
        return numpy.asarray(bytearray(content), dtype=numpy.uint8)
    except:
        traceback.print_exc()
        return None


def analyze_image(imagedata):
    try:
        image = cv2.imdecode(imagedata, cv2.IMREAD_COLOR)
        if type(image) == numpy.ndarray:
            return rep.get_index().search(image)
        else:
            return None
    except:
        traceback.print_exc()
        return None


def custom_render_template(error=None, search_results=None):
    return render_template("index.html", error=error, search_results=search_results, stats=rep.get_statistics())


if __name__ == "__main__":
    app.run(host="0.0.0.0")
