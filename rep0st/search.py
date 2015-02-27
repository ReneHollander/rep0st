from operator import attrgetter
import itertools

import cv2
import flask
import logbook
import numpy
import os

import rep0st.analyze
import rep0st.download


def shape_feature(feature):
    return feature.astype(numpy.float32).reshape((1, 3 * 36))


class ImageSearch(object):
    def __init__(self, features):
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

    @app.route("/", methods=["POST"])
    def query():
        # get and decode upload
        ifile = flask.request.files['image']
        imagedata = numpy.fromstring(ifile.read(), numpy.uint8)
        image = cv2.imdecode(imagedata, cv2.IMREAD_COLOR)

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


    @app.route("/", methods=["GET"])
    def index():
        return flask.render_template("results.html", results=None, lastIndexedPost=search.lastIndexedPost)

    return app


def main():
    app = make_webapp()
    app.run(host="0.0.0.0", port=1576, threaded=True)


if __name__ == '__main__':
    main()
