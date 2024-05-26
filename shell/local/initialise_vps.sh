#!/bin/sh

# Exit script on error
set -e

# Prompt for necessary variables
read -p "Enter the new username: " VPS_USER
read -p "Enter your email for SSH key generation: " USER_EMAIL
read -p "Enter the VPS IP address: " VPS_IP
read -p "Enter the VPS SSH port (default 22): " VPS_PORT
VPS_PORT=${VPS_PORT:-22}  # Use default port 22 if not provided
read -s -p "Enter the new user's password: " VPS_USER_PASSWORD
echo

# Generate SSH key for the new user
echo "Generating SSH key for $VPS_USER..."
ssh-keygen -t rsa -b 4096 -C "$USER_EMAIL" -N "" -f ~/.ssh/id_rsa_$VPS_USER

# Copy the generated keys to the current directory
cp ~/.ssh/id_rsa_$VPS_USER ./id_rsa_$VPS_USER.key
cp ~/.ssh/id_rsa_$VPS_USER.pub ./id_rsa_$VPS_USER.pub

# Add the new user and set up permissions on the server
ssh -p $VPS_PORT root@$VPS_IP << EOF
adduser --disabled-password --gecos "" $VPS_USER
usermod -aG sudo $VPS_USER
mkdir -p /home/$VPS_USER/.ssh
chown $VPS_USER:$VPS_USER /home/$VPS_USER/.ssh
EOF

# Set the user's password separately to avoid issues with the heredoc
ssh -p $VPS_PORT root@$VPS_IP "echo '$VPS_USER:$VPS_USER_PASSWORD' | chpasswd"

# Copy the generated public key to the server
scp -P $VPS_PORT id_rsa_$VPS_USER.pub root@$VPS_IP:/home/$VPS_USER/.ssh/authorized_keys

# Set permissions on the server
ssh -p $VPS_PORT root@$VPS_IP << EOF
chmod 700 /home/$VPS_USER/.ssh
chmod 600 /home/$VPS_USER/.ssh/authorized_keys
chown -R $VPS_USER:$VPS_USER /home/$VPS_USER/.ssh
EOF

# Install necessary packages on the server
ssh -p $VPS_PORT root@$VPS_IP << EOF
apt-get update
apt-get install -y apt-transport-https ca-certificates curl software-properties-common fail2ban
EOF

# Install Docker on the server
ssh -p $VPS_PORT root@$VPS_IP << EOF
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=\$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \$(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce
usermod -aG docker $VPS_USER
EOF

# Install the latest Docker Compose on the server
ssh -p $VPS_PORT root@$VPS_IP << EOF
DOCKER_COMPOSE_VERSION=\$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d '"' -f 4)
curl -L "https://github.com/docker/compose/releases/download/\$DOCKER_COMPOSE_VERSION/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
EOF

# Verify Docker Compose installation as the new user
ssh -p $VPS_PORT root@$VPS_IP "su - $VPS_USER -c 'docker-compose --version'"

# Configure Fail2ban for SSH protection
ssh -p $VPS_PORT root@$VPS_IP << EOF
cat <<EOT > /etc/fail2ban/jail.local
[sshd]
enabled = true
port = $VPS_PORT
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
EOT
systemctl restart fail2ban
EOF

# Disable password login for SSH at the end of the script
ssh -p $VPS_PORT root@$VPS_IP "sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config && systemctl reload sshd"

# Configure SSH client to use the generated key by default
echo "Configuring SSH client to use the generated key by default..."
echo "Host $VPS_IP
  User $VPS_USER
  Port $VPS_PORT
  IdentityFile ~/.ssh/id_rsa_$VPS_USER
" >> ~/.ssh/config

# Set permissions for the SSH config file
chmod 600 ~/.ssh/config

echo "Initial setup complete. Please log out and log back in as $VPS_USER to apply group changes."
