#!/bin/sh
cd ~/neverdrugs-reload
git pull
docker compose -f production.yml build --no-cache
docker compose -f production.yml down
docker compose -f production.yml up