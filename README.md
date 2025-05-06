1. Pip install -r requirements.txt
2. Python manage.py runserver

## Run in Docker
```commandline
docker images
docker build -t v1.0 .
docker ps -a
docker rm test
docker run --name test v1.0
docker stop test
```
## Docker compose
```commandline
docker compose -f .\docker-compose-dev.yaml up --build

```
