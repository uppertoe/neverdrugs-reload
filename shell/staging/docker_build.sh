#!/bin/sh

# Set the docker compose file
read -p "Enter the docker compose file to use: " COMPOSE_FILE

REPO_DIR=$HOME/neverdrugs-reload

# Change directory to the cloned repository
cd $REPO_DIR

# Build the Docker images
docker compose -f $COMPOSE_FILE build

# Run migrations and collectstatic
docker compose -f $COMPOSE_FILE run --rm django python manage.py migrate
docker compose -f $COMPOSE_FILE run --rm django python manage.py collectstatic --noinput

# Create Django superuser interactively
docker compose -f $COMPOSE_FILE run --rm django python manage.py createsuperuser

# Start the application
docker compose -f $COMPOSE_FILE up -d

echo "Application setup and started successfully."