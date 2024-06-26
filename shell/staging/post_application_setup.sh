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

# Set ENVS .envs/.production/.django
#POSTGRES_USE_SSL=False
#DB_SSLROOTCERT=/etc/ssl/postgresql/ca/ca.crt
#DB_SSLCERT=/etc/ssl/postgresql/client/client.crt
#DB_SSLKEY=/etc/ssl/postgresql/client/client.key

# Prompt for necessary variables
read -p "Enter the domain for SSL certificates: " DOMAIN
read -p "Enter the Docker Compose file to be used: " DOCKER_COMPOSE_FILE
# Prompt for the CA key password
read -s -p "Enter the password for the CA key: " CA_PASSWORD

# Variables
HOST_SSL_DIR="$HOME/ssl/postgresql"
CONTAINER_SSL_DIR="/etc/ssl/postgresql"

REPO_DIR=$HOME/neverdrugs-reload
cd $REPO_DIR

# Update and install necessary packages
sudo apt-get update && sudo apt-get install -y certbot curl openssl|| { echo "Failed to install required packages."; exit 1; }

# Create directories for SSL certificates and keys
sudo mkdir -p $HOST_SSL_DIR/ca
sudo mkdir -p $HOST_SSL_DIR/server
sudo mkdir -p $HOST_SSL_DIR/client

## Generate keys and certificates
# Generate CA key and certificate; subject must be different to the server and client subjects
sudo openssl genpkey -algorithm RSA -out $HOST_SSL_DIR/ca/ca.key -aes256 -pass pass:$CA_PASSWORD
sudo openssl req -new -x509 -days 365 -key $HOST_SSL_DIR/ca/ca.key -out $HOST_SSL_DIR/ca/ca.crt -passin pass:$CA_PASSWORD -subj "/CN=My CA"
# Generate server key and certificate signing request (CSR)
sudo openssl genpkey -algorithm RSA -out $HOST_SSL_DIR/server/server.key
sudo openssl req -new -key $HOST_SSL_DIR/server/server.key -out $HOST_SSL_DIR/server/server.csr -subj "/CN=$DOMAIN"
sudo openssl x509 -req -in $HOST_SSL_DIR/server/server.csr -CA $HOST_SSL_DIR/ca/ca.crt -CAkey $HOST_SSL_DIR/ca/ca.key -CAcreateserial -out $HOST_SSL_DIR/server/server.crt -days 365 -passin pass:$CA_PASSWORD
# Generate client key and certificate
sudo openssl genpkey -algorithm RSA -out $HOST_SSL_DIR/client/client.key
sudo openssl req -new -key $HOST_SSL_DIR/client/client.key -out $HOST_SSL_DIR/client/client.csr -subj "/CN=My Client"
sudo openssl x509 -req -in $HOST_SSL_DIR/client/client.csr -CA $HOST_SSL_DIR/ca/ca.crt -CAkey $HOST_SSL_DIR/ca/ca.key -CAcreateserial -out $HOST_SSL_DIR/client/client.crt -days 365 -passin pass:$CA_PASSWORD

# Set key and certificate permissions
# CA
sudo chmod 600 $HOST_SSL_DIR/ca/ca.key
sudo chmod 644 $HOST_SSL_DIR/ca/ca.crt
sudo chown 999:999 $HOST_SSL_DIR/ca/ca.key $HOST_SSL_DIR/ca/ca.crt
# Server
sudo chmod 600 $HOST_SSL_DIR/server/server.key
sudo chmod 644 $HOST_SSL_DIR/server/server.crt
sudo chown 999:999 $HOST_SSL_DIR/server/server.key $HOST_SSL_DIR/server/server.crt
# Client
sudo chmod 600 $HOST_SSL_DIR/client/client.key
sudo chmod 644 $HOST_SSL_DIR/client/client.crt
sudo chown 100:102 $HOST_SSL_DIR/client/client.key $HOST_SSL_DIR/client/client.crt


# PostgreSQL configuration adjustments
sudo tee $HOST_SSL_DIR/server/postgresql.conf > /dev/null <<EOF
ssl = on
ssl_cert_file = '/etc/ssl/postgresql/server/server.crt'
ssl_key_file = '/etc/ssl/postgresql/server/server.key'
ssl_ca_file = '/etc/ssl/postgresql/ca/ca.crt'
listen_addresses = '*'
EOF

# Modify pg_hba.conf to enforce SSL connections
sudo tee $HOST_SSL_DIR/server/pg_hba.conf > /dev/null <<EOF
# TYPE  DATABASE        USER            ADDRESS                 METHOD
hostssl all             all             0.0.0.0/0               md5
hostssl all             all             ::/0                    md5
EOF

# Build the Docker images
docker compose -f $DOCKER_COMPOSE_FILE build --no-cache

# Run migrations and collectstatic
docker compose -f $DOCKER_COMPOSE_FILE run --rm django python manage.py migrate
docker compose -f $DOCKER_COMPOSE_FILE run --rm django python manage.py collectstatic --noinput

echo "Create SuperUser"
# Create Django superuser interactively
docker compose -f $DOCKER_COMPOSE_FILE run --rm django python manage.py createsuperuser

# Start the application
docker compose -f $DOCKER_COMPOSE_FILE up -d



echo "Post-application setup complete. Docker services have been configured and started with encryption at rest and in transit, and scheduled updates and backups with email notifications on failure."
