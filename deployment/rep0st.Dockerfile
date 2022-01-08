FROM python:3.10.1 as base

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1

RUN apt-get update && apt-get dist-upgrade -y

FROM base AS python-deps

RUN apt-get install -y gcc

RUN pip install pipenv
COPY Pipfile* /
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

FROM base AS runtime

RUN apt-get install -y ffmpeg

COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

COPY --chmod=755 deployment/healthcheck/rep0st /usr/local/bin/docker-healthcheck
HEALTHCHECK CMD ["docker-healthcheck"]

COPY rep0st /rep0st/
WORKDIR /
ENTRYPOINT ["python", "-m"]

ARG BRANCH="no_branch"
ARG COMMIT="no_commit"
LABEL branch=${BRANCH}
LABEL commit=${COMMIT}
ENV COMMIT_SHA=${COMMIT}
ENV COMMIT_BRANCH=${BRANCH}
