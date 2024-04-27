FROM paradedb/paradedb:0.6.1

HEALTHCHECK CMD ["pg_isready", "-U", "rep0st", "-d", "rep0st"]

ARG BRANCH="no_branch"
ARG COMMIT="no_commit"
LABEL branch=${BRANCH}
LABEL commit=${COMMIT}
ENV COMMIT_SHA=${COMMIT}
ENV COMMIT_BRANCH=${BRANCH}
