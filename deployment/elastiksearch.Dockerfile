FROM docker.elastic.co/elasticsearch/elasticsearch:8.13.2

RUN elasticsearch-plugin install --batch https://github.com/alexklibisz/elastiknn/releases/download/8.13.2.0/elastiknn-8.13.2.0.zip

COPY --chmod=755 healthcheck/elasticsearch /usr/local/bin/docker-healthcheck
HEALTHCHECK CMD ["docker-healthcheck"]

ARG BRANCH="no_branch"
ARG COMMIT="no_commit"
LABEL branch=${BRANCH}
LABEL commit=${COMMIT}
ENV COMMIT_SHA=${COMMIT}
ENV COMMIT_BRANCH=${BRANCH}
