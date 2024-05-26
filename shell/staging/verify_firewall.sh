#!/bin/bash

# Define the SSH key path
SSH_KEY_PATH="$HOME/.ssh/authorized_keys"
read -p "Enter the VPS IP address: " VPS_IP
read -p "Enter the VPS SSH port (default 22): " VPS_PORT
VPS_PORT=${VPS_PORT:-22}  # Use default port 22 if not provided

echo "Checking UFW Status..."
sudo ufw status verbose

echo -e "\nChecking Fail2ban Status..."
sudo systemctl status fail2ban

echo -e "\nChecking Active Fail2ban Jails..."
sudo fail2ban-client status

echo -e "\nChecking Docker Status..."
sudo systemctl status docker

echo -e "\nChecking Docker Version..."
docker --version

echo -e "\nChecking Docker Compose Version..."
docker-compose --version

echo -e "\nChecking SSH Configuration..."
sudo grep -i 'passwordauthentication' /etc/ssh/sshd_config
