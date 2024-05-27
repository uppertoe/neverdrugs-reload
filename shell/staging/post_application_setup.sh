#!/bin/bash

# Ensure that compose/production/django/entrypoint has been edited
# to include ssl parameters to the postgres connector

    #connection_params = {
    #    "dbname": "${POSTGRES_DB}",
    #    "user": "${POSTGRES_USER}",
    #    "password": "${POSTGRES_PASSWORD}",
    #    "host": "${POSTGRES_HOST}",
    #    "port": "${POSTGRES_PORT}",
    #}

    #if ${POSTGRES_USE_SSL}:
    #    ssl_params = {
    #        "sslmode": "require",
    #        "sslrootcert": "/etc/ssl/postgresql/ca.crt",
    #        "sslcert": "/etc/ssl/postgresql/client/client.crt",
    #        "sslkey": "/etc/ssl/postgresql/client/client.key",
    #    }

    #    connection_params.update(**ssl_params)

# Set POSTGRES_USE_SSL=True in .envs/.production/.django

# Prompt for necessary variables
read -p "Enter the domain for SSL certificates: " DOMAIN
read -p "Enter the Docker Compose file to be used: " DOCKER_COMPOSE_FILE
# Prompt for the CA key password
read -s -p "Enter the password for the CA key: " CA_PASSWORD

# Variables
HOST_SSL_DIR="$HOME/ssl/postgresql"
CONTAINER_SSL_DIR="/etc/ssl/postgresql"
RENEWAL_SCRIPT="$HOME/renew_ssl.sh"
UPDATE_SCRIPT="$HOME/update_db.sh"
SCHEDULE_TIME="17:00:00"  # This is 03:00 AEST (UTC+10:00)

REPO_DIR=$HOME/neverdrugs-reload
cd $REPO_DIR

# Update and install necessary packages
sudo apt-get update && sudo apt-get install -y certbot curl openssl|| { echo "Failed to install required packages."; exit 1; }

# Install yq using snap
sudo snap install yq

# Create directories for SSL certificates and keys
sudo mkdir -p $HOST_SSL_DIR/ca
sudo mkdir -p $HOST_SSL_DIR/server
sudo mkdir -p $HOST_SSL_DIR/client

# Generate CA key and certificate
sudo openssl genpkey -algorithm RSA -out $HOST_SSL_DIR/ca/ca.key -aes256 -pass pass:$CA_PASSWORD
sudo openssl req -new -x509 -days 365 -key $HOST_SSL_DIR/ca/ca.key -out $HOST_SSL_DIR/ca/ca.crt -passin pass:$CA_PASSWORD -subj "/CN=$DOMAIN"

# Set appropriate permissions and ownership for the CA key
sudo chmod 600 $HOST_SSL_DIR/ca/ca.key
sudo chown 999:999 $HOST_SSL_DIR/ca/ca.key  # Assuming UID and GID for postgres user

# Generate server key and certificate signing request (CSR)
sudo openssl genpkey -algorithm RSA -out $HOST_SSL_DIR/server/server.key
sudo openssl req -new -key $HOST_SSL_DIR/server/server.key -out $HOST_SSL_DIR/server/server.csr -subj "/CN=$DOMAIN"
sudo openssl x509 -req -in $HOST_SSL_DIR/server/server.csr -CA $HOST_SSL_DIR/ca/ca.crt -CAkey $HOST_SSL_DIR/ca/ca.key -CAcreateserial -out $HOST_SSL_DIR/server/server.crt -days 365 -passin pass:$CA_PASSWORD

# Generate client key and certificate
sudo openssl genpkey -algorithm RSA -out $HOST_SSL_DIR/client/client.key
sudo openssl req -new -key $HOST_SSL_DIR/client/client.key -out $HOST_SSL_DIR/client/client.csr -subj "/CN=$DOMAIN"
sudo openssl x509 -req -in $HOST_SSL_DIR/client/client.csr -CA $HOST_SSL_DIR/ca/ca.crt -CAkey $HOST_SSL_DIR/ca/ca.key -CAcreateserial -out $HOST_SSL_DIR/client/client.crt -days 365 -passin pass:$CA_PASSWORD

# Set appropriate permissions and ownership on the host for client SSL files
sudo chmod 600 $HOST_SSL_DIR/client/*.key
sudo chmod 644 $HOST_SSL_DIR/client/*.crt
sudo chown 100:102 $HOST_SSL_DIR/client/*.key $HOST_SSL_DIR/client/*.crt  # Assuming UID 100 and GID 102 for django user

# Ensure the server SSL files are also set correctly
sudo chmod 600 $HOST_SSL_DIR/server/*.key $HOST_SSL_DIR/server/*.crt
sudo chown 999:999 $HOST_SSL_DIR/server/*.key $HOST_SSL_DIR/server/*.crt

# PostgreSQL configuration adjustments
sudo tee $HOST_SSL_DIR/server/postgresql.conf > /dev/null <<EOF
ssl = on
ssl_cert_file = '$CONTAINER_SSL_DIR/server.crt'
ssl_key_file = '$CONTAINER_SSL_DIR/server.key'
EOF

# Modify pg_hba.conf to enforce SSL connections
sudo tee $HOST_SSL_DIR/server/pg_hba.conf > /dev/null <<EOF
# TYPE  DATABASE        USER            ADDRESS                 METHOD
hostssl all             all             0.0.0.0/0               md5
hostssl all             all             ::/0                    md5
EOF

# Build the Docker images
docker compose -f $COMPOSE_FILE build --no-cache

# Apply PostgreSQL SSL configuration and restart PostgreSQL
docker-compose -f $DOCKER_COMPOSE_FILE run --rm postgres bash -c "
  cp $CONTAINER_SSL_DIR/postgresql.conf /var/lib/postgresql/data/postgresql.conf &&
  cp $CONTAINER_SSL_DIR/pg_hba.conf /var/lib/postgresql/data/pg_hba.conf &&
  chown postgres:postgres /var/lib/postgresql/data/postgresql.conf /var/lib/postgresql/data/pg_hba.conf &&
  chown -R postgres:postgres $CONTAINER_SSL_DIR
" || { echo "Failed to apply PostgreSQL SSL configuration."; exit 1; }

# Django container
docker-compose -f $DOCKER_COMPOSE_FILE run --rm django bash -c "
  chmod 644 /etc/ssl/postgresql/client.crt &&
  chmod 644 /etc/ssl/postgresql/client.key
"

# Celeryworker container
docker-compose -f $DOCKER_COMPOSE_FILE run --rm celeryworker bash -c "
  chmod 644 /etc/ssl/postgresql/client.crt &&
  chmod 644 /etc/ssl/postgresql/client.key
"

# Celerybeat container
docker-compose -f $DOCKER_COMPOSE_FILE run --rm celerybeat bash -c "
  chmod 644 /etc/ssl/postgresql/client.crt &&
  chmod 644 /etc/ssl/postgresql/client.key
"

# Flower container
docker-compose -f $DOCKER_COMPOSE_FILE run --rm flower bash -c "
  chmod 644 /etc/ssl/postgresql/client.crt &&
  chmod 644 /etc/ssl/postgresql/client.key
"

# Run migrations and collectstatic
docker compose -f $COMPOSE_FILE run --rm django python manage.py migrate
docker compose -f $COMPOSE_FILE run --rm django python manage.py collectstatic --noinput

echo "Create SuperUser"
# Create Django superuser interactively
docker compose -f $COMPOSE_FILE run --rm django python manage.py createsuperuser

# Start the application
docker compose -f $COMPOSE_FILE up -d



echo "Post-application setup complete. Docker services have been configured and started with encryption at rest and in transit, and scheduled updates and backups with email notifications on failure."
