rep0st
======
rep0st, the reverse image search for [pr0gramm](https://pr0gramm.com). Available at [rep0st.rene8888.at](https://rep0st.rene8888.at/).

# Documentation
* [API](docs/api): Documentation of the rep0st API.

## Architecture
The application unnecessarily contains a home brew framework using [Injector](https://injector.readthedocs.io/en/latest/).
It builds upon [SQLAlchemy](https://www.sqlalchemy.org/) as an ORM Mapper with MariaDB as a backing database,
[Cheroot](https://pypi.org/project/cheroot/) as a WSGI server and some custom DI stuff to glue it all together. On top
of that OpenCV is used for image processing, Elasticsearch with the [Elastiknn](https://github.com/alexklibisz/elastiknn)
plugin for indexing the features. Metrics are exported in the Prometheus format on the `/metricz` endpoints.

There is no technical reason for there being a custom framework. The author was just very bored and wanted to build
one.

## Running the application
Please run all commands from in the project root directory.

### Required software
- Docker and Docker Compose
- pyenv and pipenv

### Setup MariaDB and Elasticsearch
Start MariaDB and Elasticsearch with the correct versions locally.
```shell
docker-compose -p rep0st -f deployment/docker-compose.base.yml build
docker-compose -p rep0st -f deployment/docker-compose.base.yml up -d
```
See deployment/README.md for more info on how to run the application only
using docker and to see the settings that are used.

### Setup the Python development environment
#### Download dependencies
```shell
pipenv install --dev
```

#### Run parts of the application
The following steps should be done at least once to get the minimal state into the database
to be able to only run parts of it for development.

#### Post update job
Run the update job once and fill the database with the first 500 posts.  
Note: The application won't close after the oneshot job finished. It can
be terminated by sending a SIGINT.
```shell
pipenv run python -m rep0st.job.update_posts_job \
  --environment=DEVELOPMENT \
  --rep0st_database_uri="mysql+cymysql://rep0st:pw@localhost/rep0st?charset=utf8mb4" \
  --pr0gramm_api_user=${PR0GRAMM_API_USER?} \
  --pr0gramm_api_password=${PR0GRAMM_API_PASSWORD?} \
  --rep0st_media_path=./data/ \
  --pr0gramm_api_limit_id_to=500 \
  --rep0st_update_posts_job_schedule=oneshot
```

#### Post features job
Run the update job once and calculate features and fill the Elasticsearch index to be able to
perform lookups.
Note: The application won't close after the oneshot job finished. It can
be terminated by sending a SIGINT.
```shell
pipenv run python -m rep0st.job.update_features_job \
  --environment=DEVELOPMENT \
  --rep0st_database_uri="mysql+cymysql://rep0st:pw@localhost/rep0st?charset=utf8mb4" \
  --rep0st_media_path=./data/ \
  --rep0st_update_features_job_schedule=oneshot
```

#### Web
This runs the user facing web application serving the page, API and processing lookups.
```shell
pipenv run python -m rep0st.web \
  --environment=DEVELOPMENT \
  --rep0st_database_uri="mysql+cymysql://rep0st:pw@localhost/rep0st?charset=utf8mb4"
```

# Pull Requests
Run the autoformatter before sending a Pull Request to ensure all files are nicely formatted:
```shell
pipenv run yapf -ir rep0st
```

# Authors
- Rene Hollander ([user/Rene8888](http://pr0gramm.com/user/Rene8888))
- Patrick Malik
- mopsalarm ([user/mopsalarm](http://pr0gramm.com/user/mopsalarm))
- Vanilla-Chan ([user/TollesEinhorn](https://pr0gramm.com/user/TollesEinhorn)): API für URL Suche

# License
```
The MIT License (MIT)

Copyright (c) 2015-2021 Rene Hollander, Patrick Malik, mopsalarm and contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
