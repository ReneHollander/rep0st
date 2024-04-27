# Building and deploying rep0st and its dependencies locally

**Note: Run all commands from the project root directory.**

## Only dependencies

Starts services like PostgreSQL for developing locally.

```shell
docker-compose -p rep0st -f deployment/docker-compose.base.yml build
docker-compose -p rep0st -f deployment/docker-compose.base.yml up -d
```

Reach

- PostgreSQL at `localhost:5432`

## Full application in development mode

Starts the full application locally.

```shell
docker-compose -p rep0st -f deployment/docker-compose.base.yml -f deployment/docker-compose.app.yml build
docker-compose -p rep0st -f deployment/docker-compose.base.yml -f deployment/docker-compose.app.yml up -d
```

Reach

- PostgreSQL at `localhost:5432`
- Post update job at `localhost:5001/metricz`
- Feature update job at `localhost:5002/metricz`
- Frontend at `localhost:5000` (`localhost:5000/metricz` for metrics)

## Deploy to internal registry

```shell
docker-compose -f deployment/docker-compose.build.yml build --build-arg=COMMIT=$(git rev-parse --short HEAD) --build-arg=BRANCH=$(git rev-parse --abbrev-ref HEAD)
docker-compose -f deployment/docker-compose.build.yml push
```
