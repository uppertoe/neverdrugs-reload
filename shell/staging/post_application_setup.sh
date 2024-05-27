#!/bin/bash

# Prompt for necessary variables
read -p "Enter the email to be notified on failure: " NOTIFY_EMAIL
read -p "Enter the Sendgrid API key: " SENDGRID_API_KEY
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

# Update Docker Compose file for SSL
yq eval '.services.postgres.volumes += [{"type": "bind", "source": "'"$HOST_SSL_DIR/server"'", "target": "'"$CONTAINER_SSL_DIR"'"}]' -i $DOCKER_COMPOSE_FILE
yq eval '.services.postgres.environment += {"POSTGRES_SSL_CERT_FILE": "'"$CONTAINER_SSL_DIR/server.crt"'"}' -i $DOCKER_COMPOSE_FILE
yq eval '.services.postgres.environment += {"POSTGRES_SSL_KEY_FILE": "'"$CONTAINER_SSL_DIR/server.key"'"}' -i $DOCKER_COMPOSE_FILE
yq eval '.services.postgres.environment += {"POSTGRES_SSL": "on"}' -i $DOCKER_COMPOSE_FILE

# Ensure all services use the CA certificate to verify the server certificate
yq eval '.services.django.volumes += [{"type": "bind", "source": "'"$HOST_SSL_DIR/client"'", "target": "/etc/ssl/postgresql"}]' -i $DOCKER_COMPOSE_FILE
yq eval '.services.celeryworker.volumes += [{"type": "bind", "source": "'"$HOST_SSL_DIR/client"'", "target": "/etc/ssl/postgresql"}]' -i $DOCKER_COMPOSE_FILE
yq eval '.services.celerybeat.volumes += [{"type": "bind", "source": "'"$HOST_SSL_DIR/client"'", "target": "/etc/ssl/postgresql"}]' -i $DOCKER_COMPOSE_FILE
yq eval '.services.flower.volumes += [{"type": "bind", "source": "'"$HOST_SSL_DIR/client"'", "target": "/etc/ssl/postgresql"}]' -i $DOCKER_COMPOSE_FILE
yq eval '.services.awscli.volumes += [{"type": "bind", "source": "'"$HOST_SSL_DIR/client"'", "target": "/etc/ssl/postgresql"}]' -i $DOCKER_COMPOSE_FILE

yq eval '.services.django.environment += {"DB_SSLROOTCERT": "/etc/ssl/postgresql/ca.crt", "DB_SSLCERT": "/etc/ssl/postgresql/client.crt", "DB_SSLKEY": "/etc/ssl/postgresql/client.key"}' -i $DOCKER_COMPOSE_FILE
yq eval '.services.celeryworker.environment += {"DB_SSLROOTCERT": "/etc/ssl/postgresql/ca.crt", "DB_SSLCERT": "/etc/ssl/postgresql/client.crt", "DB_SSLKEY": "/etc/ssl/postgresql/client.key"}' -i $DOCKER_COMPOSE_FILE
yq eval '.services.celerybeat.environment += {"DB_SSLROOTCERT": "/etc/ssl/postgresql/ca.crt", "DB_SSLCERT": "/etc/ssl/postgresql/client.crt", "DB_SSLKEY": "/etc/ssl/postgresql/client.key"}' -i $DOCKER_COMPOSE_FILE
yq eval '.services.flower.environment += {"DB_SSLROOTCERT": "/etc/ssl/postgresql/ca.crt", "DB_SSLCERT": "/etc/ssl/postgresql/client.crt", "DB_SSLKEY": "/etc/ssl/postgresql/client.key"}' -i $DOCKER_COMPOSE_FILE
yq eval '.services.awscli.environment += {"DB_SSLROOTCERT": "/etc/ssl/postgresql/ca.crt", "DB_SSLCERT": "/etc/ssl/postgresql/client.crt", "DB_SSLKEY": "/etc/ssl/postgresql/client.key"}' -i $DOCKER_COMPOSE_FILE

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

# Ensure PostgreSQL reads the new configuration files
docker-compose -f $DOCKER_COMPOSE_FILE down

docker-compose -f $DOCKER_COMPOSE_FILE build

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

docker-compose -f $DOCKER_COMPOSE_FILE up -d


# Create renewal script
tee $RENEWAL_SCRIPT > /dev/null <<EOF
#!/bin/bash

# Renew the SSL certificates if they are close to expiry
if certbot renew --quiet --deploy-hook "cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $HOST_SSL_DIR/server.crt && cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $HOST_SSL_DIR/server.key && chmod 600 $HOST_SSL_DIR/server.*"; then
  # Certificates were renewed and copied, restart PostgreSQL container to apply new certificates
  docker-compose -f $DOCKER_COMPOSE_FILE restart postgres
fi
EOF

chmod +x $RENEWAL_SCRIPT

# Create update script
tee $UPDATE_SCRIPT > /dev/null <<EOF
#!/bin/bash

# Create temporary backup directory
TEMP_BACKUP_DIR=\$(mktemp -d)
if [ ! -d "\$TEMP_BACKUP_DIR" ]; then
  echo "Failed to create temporary backup directory."
  exit 1
fi

# Function to clean up temporary backup directory on exit
cleanup() {
  rm -rf "\$TEMP_BACKUP_DIR"
}
trap cleanup EXIT

# Pull the latest PostgreSQL image
docker pull docker.io/postgres:15 || { echo "Failed to pull PostgreSQL image."; exit 1; }

# Halt all containers, excluding postgres
docker-compose -f $DOCKER_COMPOSE_FILE down || { echo "Failed to stop Docker containers."; exit 1; }
docker-compose -f $DOCKER_COMPOSE_FILE up -d postgres || { echo "Failed to start PostgreSQL container."; exit 1; }

# Perform a database backup before updating
docker-compose -f $DOCKER_COMPOSE_FILE run --rm postgres backup || { echo "Database backup failed."; exit 1; }

# Copy the backup folder locally
docker cp \$(docker-compose -f $DOCKER_COMPOSE_FILE ps -q postgres):/backups \$TEMP_BACKUP_DIR || { echo "Failed to copy backups."; exit 1; }

# Check if any backups are available
LATEST_BACKUP=\$(ls -t \$TEMP_BACKUP_DIR/backups | head -1)
if [ -z "\$LATEST_BACKUP" ]; then
  echo "No backups found. Aborting update."
  exit 1
fi

# Determine the old PostgreSQL volume name
OLD_POSTGRES_VOLUME=\$(docker volume ls -q | grep _postgres_data | grep -v _postgres_data_backups)

# Delete the old PostgreSQL volume
docker volume rm \$OLD_POSTGRES_VOLUME || { echo "Failed to remove old PostgreSQL volume."; exit 1; }

# Build the new PostgreSQL image
docker-compose -f $DOCKER_COMPOSE_FILE build postgres || { echo "Failed to build PostgreSQL image."; exit 1; }

# Start the new PostgreSQL container
docker-compose -f $DOCKER_COMPOSE_FILE up -d postgres || { echo "Failed to start new PostgreSQL container."; exit 1; }

# Restore the latest backup
docker-compose -f $DOCKER_COMPOSE_FILE run --rm postgres restore /backups/\$LATEST_BACKUP || { echo "Failed to restore the latest backup."; exit 1; }

# Clean up local backups
rm -rf \$TEMP_BACKUP_DIR

# Start the rest of the containers
docker-compose -f $DOCKER_COMPOSE_FILE up -d || { echo "Failed to start Docker containers."; exit 1; }
EOF

chmod +x $UPDATE_SCRIPT

# Create notify failure script
tee $HOME/notify_failure.sh > /dev/null <<EOF
#!/bin/bash
UNIT_NAME=\$1
STATUS=\$(systemctl is-failed \$UNIT_NAME)
MESSAGE="The systemd unit \$UNIT_NAME has failed with status: \$STATUS"
curl --request POST \
  --url https://api.sendgrid.com/v3/mail/send \
  --header "Authorization: Bearer $SENDGRID_API_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "personalizations": [
      {
        "to": [
          {
            "email": "'$NOTIFY_EMAIL'"
          }
        ],
        "subject": "Systemd Unit Failure: '$UNIT_NAME'"
      }
    ],
    "from": {
      "email": "'$NOTIFY_EMAIL'"
    },
    "content": [
      {
        "type": "text/plain",
        "value": "'$MESSAGE'"
      }
    ]
  }'
EOF

chmod +x $HOME/notify_failure.sh

# Create systemd service for notification
sudo tee /etc/systemd/system/notify_failure.service > /dev/null <<EOF
[Unit]
Description=Notify on systemd unit failure

[Service]
Type=oneshot
ExecStart=$HOME/notify_failure.sh %i
EOF

# Create systemd service for renewal
sudo tee /etc/systemd/system/renew_ssl.service > /dev/null <<EOF
[Unit]
Description=Renew SSL certificates
OnFailure=notify_failure@%n.service

[Service]
Type=oneshot
ExecStart=$RENEWAL_SCRIPT
EOF

# Create systemd timer for renewal
sudo tee /etc/systemd/system/renew_ssl.timer > /dev/null <<EOF
[Unit]
Description=Run SSL renewal script daily at 03:00 AEST

[Timer]
OnCalendar=*-*-* $SCHEDULE_TIME UTC
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Create systemd service for updating PostgreSQL
sudo tee /etc/systemd/system/update_db.service > /dev/null <<EOF
[Unit]
Description=Update PostgreSQL Docker container
OnFailure=notify_failure@%n.service

[Service]
Type=oneshot
ExecStart=$UPDATE_SCRIPT
EOF

# Create systemd timer for updating PostgreSQL
sudo tee /etc/systemd/system/update_db.timer > /dev/null <<EOF
[Unit]
Description=Run PostgreSQL update script weekly at 03:00 AEST

[Timer]
OnCalendar=Mon *-*-* $SCHEDULE_TIME UTC
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start systemd timers
sudo systemctl enable renew_ssl.timer
sudo systemctl start renew_ssl.timer
sudo systemctl enable update_db.timer
sudo systemctl start update_db.timer

echo "Post-application setup complete. Docker services have been configured and started with encryption at rest and in transit, and scheduled updates and backups with email notifications on failure."
