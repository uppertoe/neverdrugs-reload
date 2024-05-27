#!/bin/sh

# Exit script on error
set -e

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

# Create the .env directories on the server
mkdir -p $REPO_DIR/.envs/.production

# Instruction to user to use scp to copy .env files
echo "Please use scp to copy your .env files to the server. Example:"
echo "scp .envs/.production/.django $VPS_USER@$VPS_IP:$REPO_DIR/.envs/.production/.django"
echo "scp .envs/.production/.postgres $VPS_USER@$VPS_IP:$REPO_DIR/.envs/.production/.postgres"

echo "Once copied, run post_application_setup.sh"

