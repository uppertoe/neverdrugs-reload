#!/bin/bash

read -p "Enter the email to be notified on failure: " NOTIFY_EMAIL
read -p "Enter the Sendgrid API key: " SENDGRID_API_KEY
read -p "Enter the domain for SSL certificates: " DOMAIN
read -p "Enter the Docker Compose file to be used: " DOCKER_COMPOSE_FILE

# Variables
HOST_SSL_DIR="$HOME/ssl/postgresql"
CONTAINER_SSL_DIR="/etc/ssl/postgresql"
RENEWAL_SCRIPT="$HOME/renew_ssl.sh"
UPDATE_SCRIPT="$HOME/update_db.sh"
SCHEDULE_TIME="17:00:00"  # This is 03:00 AEST (UTC+10:00)

REPO_DIR=$HOME/neverdrugs-reload
cd $REPO_DIR

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