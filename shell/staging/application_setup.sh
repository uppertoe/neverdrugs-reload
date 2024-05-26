#!/bin/sh

# Exit script on error
set -e

# Set the docker compose file
read -p "Enter the docker compose file to use: " COMPOSE_FILE

# Get the current VPS IP address and username
VPS_IP=$(hostname -I | awk '{print $1}')
VPS_USER=$(whoami)

echo "Detected VPS IP: $VPS_IP"
echo "Detected VPS User: $VPS_USER"

# Set up the repository
REPO_DIR=$HOME/neverdrugs-reload
if [ -d "$REPO_DIR" ]; then
    echo "Repository already exists. Pulling the latest changes..."
    cd $REPO_DIR
    git pull
else
    echo "Cloning the repository..."
    git clone https://github.com/uppertoe/neverdrugs-reload.git $REPO_DIR
fi

# Instruction to user to use scp to copy .env files
echo "Please use scp to copy your .env files to the server. Example:"
echo "scp .envs/.production/.django $VPS_USER@$VPS_IP:$REPO_DIR/.envs/.production/.django"
echo "scp .envs/.production/.postgres $VPS_USER@$VPS_IP:$REPO_DIR/.envs/.production/.postgres"

# Wait for user to copy the files
read -p "Press enter after you have copied the .env files to the server..."

# Change directory to the cloned repository
cd $REPO_DIR

# Build the Docker images
docker-compose -f $COMPOSE_FILE build

# Run migrations and collectstatic
docker-compose -f $COMPOSE_FILE run --rm django python manage.py migrate
docker-compose -f $COMPOSE_FILE run --rm django python manage.py collectstatic --noinput

# Create Django superuser interactively
docker-compose -f $COMPOSE_FILE run --rm django python manage.py createsuperuser

# Start the application
docker-compose -f $COMPOSE_FILE up -d

echo "Application setup and started successfully."
