#!/bin/bash

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
