#!/bin/bash

docker login rg.fr-par.scw.cloud/djnd -u nologin -p $SCW_SECRET_TOKEN

docker build -f ./backend/Dockerfile -t tea-ostani-api:latest ./backend
docker tag tea-ostani-api:latest rg.fr-par.scw.cloud/djnd/tea-ostani-api:latest
docker push rg.fr-par.scw.cloud/djnd/tea-ostani-api:latest

docker build -f ./Dockerfile -t tea-ostani:latest .
docker tag tea-ostani:latest rg.fr-par.scw.cloud/djnd/tea-ostani:latest
docker push rg.fr-par.scw.cloud/djnd/tea-ostani:latest
