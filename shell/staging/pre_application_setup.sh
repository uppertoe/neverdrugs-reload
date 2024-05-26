#!/bin/sh

# Sets up encrypted volumes for Postgres and its local backups
# Uses Certbot, with scheduled updating of certificates

# docker-compose.yml should be configured:
#    volumes:
#      - type: bind
#        source: /var/lib/docker/pgdata/postgresql
#        target: /var/lib/postgresql/data
#      - type: bind
#        source: /var/lib/docker/pgbackups/backups
#        target: /backups

# ----------------------------------------------------------------

# Exit script on error
set -e

# Ensure the script is running as root
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root"
  exit 1
fi

# Prompt for variables
read -p "Enter the domain for this website: " DOMAIN
read -p "Enter the email to use with certbot: " CERTBOT_EMAIL

# Variables
HOST_SSL_DIR="/etc/ssl/postgresql"
ENCRYPTED_DATA_FILE="/var/lib/docker/encrypted-pgdata"
ENCRYPTED_BACKUP_FILE="/var/lib/docker/encrypted-pgbackups"
ENCRYPTED_DATA_VOLUME="/var/lib/docker/pgdata"
ENCRYPTED_BACKUP_VOLUME="/var/lib/docker/pgbackups"
DATA_KEY_FILE="/etc/luks-keys/pgdata.key"  # Path to store the LUKS key for data
BACKUP_KEY_FILE="/etc/luks-keys/pgbackups.key"  # Path to store the LUKS key for backups

# Update and install necessary packages
apt-get update && apt-get install -y certbot cryptsetup parted curl || { echo "Failed to install required packages."; exit 1; }

# Generate LUKS keys and store them securely
mkdir -p /etc/luks-keys
dd if=/dev/urandom of=$DATA_KEY_FILE bs=4096 count=1
dd if=/dev/urandom of=$BACKUP_KEY_FILE bs=4096 count=1
chmod 600 /etc/luks-keys/*.key
chown root:root /etc/luks-keys/*.key

# Create and set up the encrypted data volume using LUKS
echo "Creating encrypted data volume..."
dd if=/dev/zero of=$ENCRYPTED_DATA_FILE bs=1M count=1024
cryptsetup luksFormat $ENCRYPTED_DATA_FILE $DATA_KEY_FILE
cryptsetup luksOpen $ENCRYPTED_DATA_FILE pgdata_encrypted --key-file $DATA_KEY_FILE
mkfs.ext4 /dev/mapper/pgdata_encrypted
mkdir -p $ENCRYPTED_DATA_VOLUME
mount /dev/mapper/pgdata_encrypted $ENCRYPTED_DATA_VOLUME
mkdir -p $ENCRYPTED_DATA_VOLUME/postgresql

# Ensure the postgres user owns the directory
chown -R postgres:postgres $ENCRYPTED_DATA_VOLUME/postgresql

# Create and set up the encrypted backup volume using LUKS
echo "Creating encrypted backup volume..."
dd if=/dev/zero of=$ENCRYPTED_BACKUP_FILE bs=1M count=1024
cryptsetup luksFormat $ENCRYPTED_BACKUP_FILE $BACKUP_KEY_FILE
cryptsetup luksOpen $ENCRYPTED_BACKUP_FILE pgbackups_encrypted --key-file $BACKUP_KEY_FILE
mkfs.ext4 /dev/mapper/pgbackups_encrypted
mkdir -p $ENCRYPTED_BACKUP_VOLUME
mount /dev/mapper/pgbackups_encrypted $ENCRYPTED_BACKUP_VOLUME
mkdir -p $ENCRYPTED_BACKUP_VOLUME/backups

# Ensure the volumes mount automatically at boot
echo '/dev/mapper/pgdata_encrypted /var/lib/docker/pgdata ext4 defaults 0 2' | tee -a /etc/fstab
echo '/dev/mapper/pgbackups_encrypted /var/lib/docker/pgbackups ext4 defaults 0 2' | tee -a /etc/fstab
echo 'pgdata_encrypted /var/lib/docker/encrypted-pgdata none luks,discard' | tee -a /etc/crypttab
echo 'pgbackups_encrypted /var/lib/docker/encrypted-pgbackups none luks,discard' | tee -a /etc/crypttab

# Create directories for SSL certificates and keys
mkdir -p $HOST_SSL_DIR

# Generate SSL certificates using Certbot
certbot certonly --standalone -d $DOMAIN --email $CERTBOT_EMAIL --agree-tos --non-interactive || { echo "Certbot certificate generation failed."; exit 1; }
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $HOST_SSL_DIR/server.crt
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $HOST_SSL_DIR/server.key
chown root:root $HOST_SSL_DIR/server.*
chmod 600 $HOST_SSL_DIR/server.*

echo "Encrypted Docker volumes and SSL certificates have been set up."

# Troubleshooting permissions
echo "Checking permissions..."
ls -ld $ENCRYPTED_DATA_VOLUME/postgresql
ls -ld $ENCRYPTED_BACKUP_VOLUME/backups
