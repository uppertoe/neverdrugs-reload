#!/bin/bash

# Exit script on error
set -e

# Ensure the script is running as root
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root"
  exit 1
fi

# Variables
ENCRYPTED_DATA_FILE="/var/lib/docker/encrypted-pgdata"
ENCRYPTED_BACKUP_FILE="/var/lib/docker/encrypted-pgbackups"

# Remove existing LUKS devices if they exist
if cryptsetup status pgdata_encrypted >/dev/null 2>&1; then
  echo "Removing existing encrypted data volume..."
  umount /dev/mapper/pgdata_encrypted || true
  cryptsetup luksClose pgdata_encrypted || true
  rm -f $ENCRYPTED_DATA_FILE
fi

if cryptsetup status pgbackups_encrypted >/dev/null 2>&1; then
  echo "Removing existing encrypted backup volume..."
  umount /dev/mapper/pgbackups_encrypted || true
  cryptsetup luksClose pgbackups_encrypted || true
  rm -f $ENCRYPTED_BACKUP_FILE
fi

echo "Existing encrypted volumes have been removed."
