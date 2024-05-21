#!/bin/sh

## Initial server setup ##
# Setup a new user
adduser uppertoe
# Add to sudo group
usermod -aG sudo uppertoe

# Setup firewall
ufw allow OpenSSH
ufw enable

# Copy the SSH private key for the new user
rsync --archive --chown=uppertoe:uppertoe ~/.ssh /home/uppertoe

## Docker setup ##
sudo apt update
sudo apt install apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
sudo apt update
apt-cache policy docker-ce
sudo apt install docker-ce

# Check that Docker is running
sudo systemctl status docker

# Add Docker to the new user
sudo usermod -aG docker uppertoe
su - uppertoe

# Install Docker Compose
# From https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-compose-on-ubuntu-22-04
mkdir -p ~/.docker/cli-plugins/
curl -SL https://github.com/docker/compose/releases/download/v2.3.3/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-compose

# Check the version
docker compose version

# Set overcommit to 1 for Redis
echo 'vm.overcommit_memory = 1' | sudo tee -a /etc/sysctl.conf