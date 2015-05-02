from operator import attrgetter
import itertools

import cv2
import flask
import logbook
import numpy
import os
import sys
import atexit
import traceback
import requests

import rep0st.analyze
import rep0st.download


def shape_feature(feature):
    return feature.astype(numpy.float32).reshape((1, 3 * 36))


class ImageSearch(object):
    def __init__(self, features):
        atexit.register(rep0st.analyze.close_feature_file, features=features)

        """Creates a new ImageSearch instance.

        :param features: A numpy array. Each row represents one feature and its metadata.
        """
        self.flann = cv2.FlannBasedMatcher(
            {"algorithm": 1, "trees": 1}, {"checks": 5000})

        self.mapping = []
        for idx, feature in enumerate(features):
            if not feature[0]:
                continue

            # add the feature vector
            self.flann.add([shape_feature(feature[1:])])
            self.mapping.append(idx)

        logbook.info("initialized with {} features", len(self.mapping))
        self.lastIndexedPost = self.mapping[len(self.mapping) - 1]

        self.flann.train()
        logbook.info("training finished")

    def query(self, needle, k=8):
        """Queries images with the given feature."""
        needle = shape_feature(needle)

        # do a knn-search
        matches = self.flann.knnMatch(needle, k=k)
        matches = sorted(itertools.chain.from_iterable(matches),
                         key=attrgetter("distance"))

        # map back from result-id to post-id
        return [(self.mapping[match.imgIdx], match.distance) for match in matches]


def create_image_search():
    features = rep0st.analyze.mmap_feature_file()
    return ImageSearch(features)

def make_webapp():
    search = create_image_search()
    posts = rep0st.download.open_dataset()["posts"]
    tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../templates')
    app = flask.Flask(__name__, template_folder=tmpl_dir)

    def fileValid(ifile):
        ifile.seek(0, os.SEEK_END)
        if ifile == '' or ifile.tell() == 0:
            return False
        ifile.seek(0)
        return True;

    @app.route("/", methods=["POST"])
    def query():
        url =  flask.request.form.get("url")
        ifile = flask.request.files['image']

        if url != "" and fileValid(ifile):
            return flask.render_template("results.html", lastIndexedPost=search.lastIndexedPost, error="Du kannst nicht nach einer URL und einem Bild gleichzeitig suchen!")
        else:
            try:
                if url != "":
                    return checkUrl(url)
                elif fileValid(ifile):
                    # check image
                    imagedata = numpy.fromstring(ifile.read(), numpy.uint8)
                    return checkImage(imagedata)
                else:
                    return flask.render_template("results.html", lastIndexedPost=search.lastIndexedPost, error="Keine URL oder Bild angegeben!")
            except:
                traceback.print_exc()
                return flask.render_template("results.html", lastIndexedPost=search.lastIndexedPost, error="Ein unbekannter Fehler ist aufgetreten!")

    @app.route("/checkurl/<path:url>", methods=["GET"])
    def queryUrl(url):
        return checkUrl(url)

    def checkUrl(url):
        # check url
        try:
            resp = requests.get(url)
        except:
            return flask.render_template("results.html", lastIndexedPost=search.lastIndexedPost, error="Ungueltige URL!")
        resp.raise_for_status()
        content = resp.content
        return checkImage(numpy.asarray(bytearray(content), dtype=numpy.uint8))

    def checkImage(imagedata):
        try:
            image = cv2.imdecode(imagedata, cv2.IMREAD_COLOR)
            if (type(image) != numpy.ndarray):
                return flask.render_template("results.html", lastIndexedPost=search.lastIndexedPost, error="Ungueltiges Bild!")

            # build feature vector for uploaded image
            needle = rep0st.analyze.build_feature_vector_for_image(image)

            # look for matches
            results = []
            for pid, distance in search.query(needle):
                if distance > 500:
                    continue

                post = posts.find_one(id=pid)
                if post is None:
                    continue

                results.append(rep0st.download.Post(**post))

            return flask.render_template("results.html", results=results, lastIndexedPost=search.lastIndexedPost)
        except Exception as ex:
            traceback.print_exc()
            return flask.render_template("results.html", lastIndexedPost=search.lastIndexedPost, error="Unbekannter Fehler: " + str(ex))

    @app.route("/", methods=["GET"])
    def index():
        return flask.render_template("results.html", lastIndexedPost=search.lastIndexedPost)

    return app


def main():
    app = make_webapp()
    app.run(host="0.0.0.0", port=1576, threaded=True)


if __name__ == '__main__':
    main()
