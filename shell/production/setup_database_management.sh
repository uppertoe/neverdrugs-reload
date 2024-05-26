#!/bin/bash

# Ensure required environment variables are set
if [ -z "$SENDGRID_API_KEY" ] || [ -z "$NOTIFY_EMAIL" ] || [ -z "$DOMAIN" ] || [ -z "$CERTBOT_EMAIL" ] || [ -z "$DOCKER_COMPOSE_FILE" ]; then
  echo "SENDGRID_API_KEY, NOTIFY_EMAIL, DOMAIN, CERTBOT_EMAIL, and DOCKER_COMPOSE_FILE environment variables must be set."
  exit 1
fi

# Expand $HOME in DOCKER_COMPOSE_FILE
DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE/#\~/$HOME}"

# Variables
HOST_SSL_DIR="/etc/ssl/postgresql"
CONTAINER_SSL_DIR="/etc/ssl/postgresql"
RENEWAL_SCRIPT="/usr/local/bin/renew_ssl.sh"
UPDATE_SCRIPT="/usr/local/bin/update_db.sh"
SCHEDULE_TIME="17:00:00"  # This is 03:00 AEST (UTC+10:00)
ENCRYPTED_VOLUME="/var/lib/postgresql_encrypted"
LUKS_CONTAINER="/dev/mapper/postgres_encrypted"
PARTITION_SIZE="2G"

# Update and install necessary packages
sudo apt-get update && sudo apt-get install -y certbot docker-compose cryptsetup parted curl || { echo "Failed to install required packages."; exit 1; }

# Determine the primary disk dynamically
DISK=$(lsblk -ndo NAME,TYPE | grep disk | head -n 1 | awk '{print "/dev/" $1}')

# Create a new 2GB partition for PostgreSQL using parted
sudo parted $DISK --script mkpart primary ext4 0% $PARTITION_SIZE
sudo partprobe $DISK  # Inform the OS of partition table changes
PARTITION=$(lsblk -lnpo NAME,SIZE,TYPE $DISK | grep part | tail -n 1 | awk '{print $1}')

# Create and set up the encrypted volume using LUKS
echo "Creating LUKS encrypted volume on $PARTITION..."
sudo cryptsetup luksFormat $PARTITION
sudo cryptsetup open $PARTITION postgres_encrypted
sudo mkfs.ext4 $LUKS_CONTAINER
sudo mkdir -p $ENCRYPTED_VOLUME/data $ENCRYPTED_VOLUME/backups
sudo mount $LUKS_CONTAINER $ENCRYPTED_VOLUME

# Ensure the volume mounts automatically
echo "$LUKS_CONTAINER $ENCRYPTED_VOLUME ext4 defaults 0 2" | sudo tee -a /etc/fstab

# Create directories for SSL certificates and keys
sudo mkdir -p $HOST_SSL_DIR

# Generate SSL certificates using Certbot
sudo certbot certonly --standalone -d $DOMAIN --email $CERTBOT_EMAIL --agree-tos --non-interactive || { echo "Certbot certificate generation failed."; exit 1; }
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $HOST_SSL_DIR/server.crt
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $HOST_SSL_DIR/server.key
sudo chown root:root $HOST_SSL_DIR/server.*
sudo chmod 600 $HOST_SSL_DIR/server.*

# Create renewal script
sudo tee $RENEWAL_SCRIPT > /dev/null <<EOF
#!/bin/bash

# Renew the SSL certificates if they are close to expiry
if certbot renew --quiet --deploy-hook "cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $HOST_SSL_DIR/server.crt && cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $HOST_SSL_DIR/server.key && chown root:root $HOST_SSL_DIR/server.* && chmod 600 $HOST_SSL_DIR/server.*"; then
  # Certificates were renewed and copied, restart PostgreSQL container to apply new certificates
  docker-compose -f $DOCKER_COMPOSE_FILE restart postgres
fi
EOF

sudo chmod +x $RENEWAL_SCRIPT

# Create update script
sudo tee $UPDATE_SCRIPT > /dev/null <<EOF
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

sudo chmod +x $UPDATE_SCRIPT

# Create notify failure script
sudo tee /usr/local/bin/notify_failure.sh > /dev/null <<EOF
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

sudo chmod +x /usr/local/bin/notify_failure.sh

# Create systemd service for notification
sudo tee /etc/systemd/system/notify_failure.service > /dev/null <<EOF
[Unit]
Description=Notify on systemd unit failure

[Service]
Type=oneshot
ExecStart=/usr/local/bin/notify_failure.sh %i
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

# PostgreSQL configuration file adjustments
# Assuming the directory is mounted correctly in the Docker container
sudo tee $HOST_SSL_DIR/postgresql.conf > /dev/null <<EOF
ssl = on
ssl_cert_file = '$CONTAINER_SSL_DIR/server.crt'
ssl_key_file = '$CONTAINER_SSL_DIR/server.key'
EOF

# Modify pg_hba.conf to enforce SSL connections
sudo tee $HOST_SSL_DIR/pg_hba.conf > /dev/null <<EOF
# TYPE  DATABASE        USER            ADDRESS                 METHOD
hostssl all             all             0.0.0.0/0               md5
hostssl all             all             ::/0                    md5
EOF

# Restart PostgreSQL container to apply changes
docker-compose -f $DOCKER_COMPOSE_FILE restart postgres || { echo "Failed to restart PostgreSQL container."; exit 1; }

echo "Setup complete. PostgreSQL is now configured with encryption at rest and in transit, and scheduled updates and backups with email notifications on failure."
