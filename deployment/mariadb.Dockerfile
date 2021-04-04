FROM mariadb:10.5.9-focal

COPY --chmod=755 healthcheck/mariadb /usr/local/bin/docker-healthcheck
HEALTHCHECK CMD ["docker-healthcheck"]

ARG BRANCH="no_branch"
ARG COMMIT="no_commit"
LABEL branch=${BRANCH}
LABEL commit=${COMMIT}
ENV COMMIT_SHA=${COMMIT}
ENV COMMIT_BRANCH=${BRANCH}
